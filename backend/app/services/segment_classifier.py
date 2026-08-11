import math
import gzip
import io
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, time, timedelta, timezone

from app.db.database import get_db
from app.core.config import settings
from app.services.matching import geocode_address


BASE_OPERACOES_PADRAO = (-20.26548, -40.29589)  # (lat, lon)


def calcular_distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Raio da Terra em metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def _parse_timestamp(ts_val: Any) -> Optional[datetime]:
    if not ts_val:
        return None
    if isinstance(ts_val, datetime):
        return ts_val.replace(tzinfo=None)
    try:
        dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except Exception:
        return None


async def obter_pontos_jornada(jornada: dict, db) -> List[Dict[str, Any]]:
    """
    Recupera a lista de pontos de GPS da jornada.
    Tenta em ordem: 1) MinIO telemetria_url, 2) historico_gps, 3) polylines salvas.
    """
    telemetria_url = jornada.get("telemetria_url")
    if telemetria_url:
        try:
            from app.routers.uploads import MINIO_CLIENT, MINIO_BUCKET, MINIO_ENABLED
            if MINIO_ENABLED and MINIO_CLIENT:
                object_name = telemetria_url.lstrip("/").replace("app-jornada/", "")
                resp = MINIO_CLIENT.get_object(MINIO_BUCKET, object_name)
                data_bytes = resp.read()
                with gzip.GzipFile(fileobj=io.BytesIO(data_bytes)) as f:
                    pts = json.loads(f.read().decode("utf-8"))
                    if pts:
                        return pts
        except Exception as e:
            print("[CLASSIFIER] Aviso ao carregar do MinIO:", e)

    j_id = str(jornada.get("_id") or jornada.get("id"))
    pontos_db = await db["historico_gps"].find({"jornada_id": j_id}).sort("timestamp", 1).to_list(100000)
    if pontos_db:
        return pontos_db

    if jornada.get("segmentos_rota"):
        from app.routers.gps import decode_polyline
        pts = []
        for seg in jornada["segmentos_rota"]:
            try:
                dec = decode_polyline(seg.get("polyline", ""))
                is_p = seg.get("is_produtivo", False)
                for lat, lon in dec:
                    pts.append({"lat": lat, "lon": lon, "produtivo": is_p})
            except Exception:
                pass
        return pts

    return []


def classificar_segmento(
    coords: List[Tuple[float, float]],  # List of (lat, lon)
    is_produtivo_flag: bool,
    proxima_corrida_inicio: Optional[Tuple[float, float]],
    base_coords: Tuple[float, float] = BASE_OPERACOES_PADRAO,
    tem_prestacao_contas: bool = True
) -> Dict[str, Any]:
    if not coords or len(coords) < 2:
        return {
            "status": "nao_identificado",
            "rotulo": "Trajeto Não Identificado",
            "cor": "#94a3b8",
            "coords": coords
        }

    # 1. Se é uma corrida produtiva confirmada
    if is_produtivo_flag:
        return {
            "status": "produtivo",
            "rotulo": "Corrida Produtiva",
            "cor": "#10b981",  # Verde
            "coords": coords
        }

    # Se ainda não houve prestação de contas
    if not tem_prestacao_contas:
        return {
            "status": "nao_identificado",
            "rotulo": "Trajeto Não Identificado (Pré-prestação)",
            "cor": "#94a3b8",  # Cinza
            "coords": coords
        }

    p_inicio = coords[0]  # (lat, lon)
    p_fim = coords[-1]    # (lat, lon)

    # 2. Verificar se está deslocando a favor da próxima corrida
    if proxima_corrida_inicio:
        dist_inicio_a_corrida = calcular_distancia_m(p_inicio[0], p_inicio[1], proxima_corrida_inicio[0], proxima_corrida_inicio[1])
        dist_fim_a_corrida = calcular_distancia_m(p_fim[0], p_fim[1], proxima_corrida_inicio[0], proxima_corrida_inicio[1])

        if dist_fim_a_corrida < dist_inicio_a_corrida - 80:
            return {
                "status": "deslocamento",
                "rotulo": "Deslocamento p/ Início de Corrida",
                "cor": "#f59e0b",  # Amarelo / Laranja
                "coords": coords
            }

    # 3. Analisar vetor em relação à Base de Operações
    dist_inicio_a_base = calcular_distancia_m(p_inicio[0], p_inicio[1], base_coords[0], base_coords[1])
    dist_fim_a_base = calcular_distancia_m(p_fim[0], p_fim[1], base_coords[0], base_coords[1])

    if dist_fim_a_base < dist_inicio_a_base - 80:
        # Aproximando da base
        return {
            "status": "improdutivo_a_favor_base",
            "rotulo": "Deslocamento em Direção à Base",
            "cor": "#3b82f6",  # Azul
            "coords": coords
        }
    else:
        # Afastando da base e sem ir para corrida
        return {
            "status": "improdutivo_contra_base",
            "rotulo": "Improdutivo (Afastando da Base)",
            "cor": "#ef4444",  # Vermelho
            "coords": coords
        }


async def classificar_jornada_segmentos(
    pontos_gps: List[Dict[str, Any]],
    comprovantes: List[Dict[str, Any]],
    base_coords: Tuple[float, float] = BASE_OPERACOES_PADRAO,
    jornada_data_str: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Processa os pontos de GPS e cruza com os comprovantes (usando Horário PADRÃO OURO + Google Geocoding).
    """
    if not pontos_gps or len(pontos_gps) < 2:
        return []

    tem_prestacao = len(comprovantes) > 0
    api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY

    # 1. Construir janelas de tempo de corridas (PADRÃO OURO - HORÁRIO) + Geocoding Google
    janelas_corridas: List[Dict[str, Any]] = []
    ref_date = date.today()
    if jornada_data_str:
        try:
            ref_date = date.fromisoformat(jornada_data_str)
        except Exception:
            pass

    for idx_c, c in enumerate(comprovantes):
        horario_str = c.get("horario") or c.get("data_hora")
        if not horario_str:
            continue
        try:
            if "T" in str(horario_str):
                c_dt = datetime.fromisoformat(str(horario_str).replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                parts = str(horario_str).strip().split(":")
                h = int(parts[0])
                m = int(parts[1])
                c_dt = datetime.combine(ref_date, time(h, m))
            
            duracao_mins = 20
            valor = float(c.get("valor", 0.0))
            if valor > 30:
                duracao_mins = 35
            elif valor > 20:
                duracao_mins = 25
            
            dt_inicio = c_dt - timedelta(minutes=2)
            dt_fim = c_dt + timedelta(minutes=duracao_mins)

            # Geocodificar origem e destino via Google Locals se necessário
            orig_coords = c.get("origem_coords")
            dest_coords = c.get("destino_coords")

            if not orig_coords and c.get("origem") and api_key:
                try:
                    res_orig = await geocode_address(c["origem"], api_key)
                    if res_orig:
                        orig_coords = list(res_orig)
                        c["origem_coords"] = orig_coords
                except Exception:
                    pass

            if not dest_coords and c.get("destino") and api_key:
                try:
                    res_dest = await geocode_address(c["destino"], api_key)
                    if res_dest:
                        dest_coords = list(res_dest)
                        c["destino_coords"] = dest_coords
                except Exception:
                    pass

            janelas_corridas.append({
                "idx": idx_c,
                "dt_inicio": dt_inicio,
                "dt_fim": dt_fim,
                "origem_coords": orig_coords,
                "destino_coords": dest_coords
            })
        except Exception as err:
            print(f"[CLASSIFIER] Erro ao processar comprovante #{idx_c} '{horario_str}': {err}")

    comprovantes_vinculados_map = {}

    # 2. Atribuir flag produtivo para pontos GPS que caem no Horário Padrão Ouro + Proximidade Google Locals
    pontos_processados = []
    for p in pontos_gps:
        lat = p.get("lat") or p.get("localizacao", {}).get("coordinates", [0, 0])[1]
        lon = p.get("lon") or p.get("localizacao", {}).get("coordinates", [0, 0])[0]
        ts_dt = _parse_timestamp(p.get("timestamp"))

        is_prod = p.get("produtivo", False)
        if not is_prod and ts_dt and janelas_corridas:
            for item in janelas_corridas:
                idx_c = item["idx"]
                j_ini = item["dt_inicio"]
                j_fim = item["dt_fim"]

                if j_ini <= ts_dt <= j_fim:
                    is_prod = True
                    match_type = "HORARIO_EXATO"

                    # Se tiver coordenadas Google Places, validar proximidade geográfica (verificação dupla)
                    o_c = item.get("origem_coords")
                    d_c = item.get("destino_coords")
                    if o_c:
                        dist_o = calcular_distancia_m(lat, lon, o_c[0], o_c[1])
                        if dist_o <= 600:
                            match_type = "HORARIO_E_GOOGLE_LOCALS"
                    if d_c:
                        dist_d = calcular_distancia_m(lat, lon, d_c[0], d_c[1])
                        if dist_d <= 600:
                            match_type = "HORARIO_E_GOOGLE_LOCALS"

                    comprovantes_vinculados_map[idx_c] = match_type
                    break

        pontos_processados.append({
            "lat": lat,
            "lon": lon,
            "timestamp": ts_dt,
            "produtivo": is_prod
        })

    # 3. Atualizar cada comprovante com o selo de verificação de telemetria
    for idx_c, c in enumerate(comprovantes):
        if idx_c in comprovantes_vinculados_map:
            c["identificado_telemetria"] = True
            c["match_status"] = comprovantes_vinculados_map[idx_c]
        else:
            c["identificado_telemetria"] = False
            c["match_status"] = "SEM_TELEMETRIA"

    # 4. Agrupar em segmentos homogêneos de rota
    raw_segments = []
    curr_segment = []
    curr_flag = pontos_processados[0]["produtivo"]

    for p in pontos_processados:
        lat, lon = p["lat"], p["lon"]
        p_flag = p["produtivo"]

        if p_flag != curr_flag and len(curr_segment) > 0:
            curr_segment.append((lat, lon))
            raw_segments.append({"coords": curr_segment, "is_produtivo": curr_flag})
            curr_segment = [(lat, lon)]
            curr_flag = p_flag
        else:
            curr_segment.append((lat, lon))

    if len(curr_segment) > 1:
        raw_segments.append({"coords": curr_segment, "is_produtivo": curr_flag})

    pontos_inicio_corridas = []
    for idx, seg in enumerate(raw_segments):
        if seg["is_produtivo"] and len(seg["coords"]) > 0:
            pontos_inicio_corridas.append((idx, seg["coords"][0]))

    segmentos_classificados = []
    for idx, seg in enumerate(raw_segments):
        proxima_corrida = None
        for corr_idx, pt_corrida in pontos_inicio_corridas:
            if corr_idx > idx:
                proxima_corrida = pt_corrida
                break

        res = classificar_segmento(
            coords=seg["coords"],
            is_produtivo_flag=seg["is_produtivo"],
            proxima_corrida_inicio=proxima_corrida,
            base_coords=base_coords,
            tem_prestacao_contas=tem_prestacao
        )
        segmentos_classificados.append(res)

    return segmentos_classificados
