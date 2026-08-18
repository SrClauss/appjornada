from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from bson import ObjectId
import httpx
import math

from app.db.database import get_db
from app.models.historico_gps import GeoPoint, HistoricoGPS, HistoricoGPSCreate, HistoricoGPSBatch
from app.models.user import Role, UserPublic
from app.core.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.services.segment_classifier import classificar_jornada_segmentos, obter_pontos_jornada, BASE_OPERACOES_PADRAO

# Limiar para considerar motorista parado (metros)
LIMIAR_PARADO_M = 50
# Tempo máximo parado sem justificativa para gerar alerta (minutos)
MINUTOS_INATIVIDADE_ALERTA = 15

router = APIRouter(prefix="/gps", tags=["gps"])


def calcular_distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Raio da Terra em metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


async def tentar_mesclar_ponto_gps(db, motorista_id, jornada_id, timestamp, coords_lon, coords_lat, distancia_ultima_m, status, rua):
    # Busca o último ponto gravado desta jornada e motorista
    last_pt = await db["historico_gps"].find_one(
        {"motorista_id": motorista_id, "jornada_id": jornada_id},
        sort=[("timestamp", -1)]
    )
    if last_pt:
        last_coords = last_pt.get("localizacao", {}).get("coordinates", [])
        if len(last_coords) >= 2:
            last_lon, last_lat = last_coords[0], last_coords[1]
            dist = calcular_distancia_m(last_lat, last_lon, coords_lat, coords_lon)
            
            # Mesclar pontos com distância inferior a 2.0 metros (mesma posição essencial)
            limiar = 2.0
            
            if dist < limiar:
                contador = last_pt.get("contador_mesclados", 1) + 1
                await db["historico_gps"].update_one(
                    {"_id": last_pt["_id"]},
                    {"$set": {
                        "contador_mesclados": contador,
                        "timestamp": timestamp,
                        "distancia_ultima_m": distancia_ultima_m or last_pt.get("distancia_ultima_m"),
                    }}
                )
                return last_pt["_id"]
    return None


async def obter_rua_por_coordenadas(lat: float, lon: float, db) -> str:
    # 1. Tenta OSRM nearest para obter a rua e a coordenada "snapped" oficial
    snapped_lon = lon
    snapped_lat = lat
    osrm_name = ""
    try:
        url = f"{settings.OSRM_URL}/nearest/v1/driving/{lon},{lat}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=1.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("waypoints"):
                    wp = data["waypoints"][0]
                    osrm_name = (wp.get("name") or "").strip()
                    loc = wp.get("location")
                    if loc and len(loc) >= 2:
                        snapped_lon, snapped_lat = loc[0], loc[1]
                    if osrm_name:
                        return osrm_name
    except Exception as e:
        print("Erro ao obter rua via OSRM:", e)

    # 2. Se a rua veio vazia ou "Rua não identificada", busca no MongoDB ruas_customizadas próximas (raio de 35 metros)
    try:
        ponto_proximo = await db["ruas_customizadas"].find_one({
            "coordenada": {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [snapped_lon, snapped_lat]
                    },
                    "$maxDistance": 35.0
                }
            }
        })
        if ponto_proximo and ponto_proximo.get("nome_rua"):
            return ponto_proximo["nome_rua"]
    except Exception as e:
        print("Erro ao buscar no cache do MongoDB ruas_customizadas:", e)

    # 3. Tenta Google Maps Reverse Geocoding se a chave estiver configurada
    if settings.GOOGLE_API_KEY:
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "latlng": f"{lat},{lon}",
                "key": settings.GOOGLE_API_KEY,
                "language": "pt-BR"
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "OK" and data.get("results"):
                        google_name = ""
                        # 1. Procura em todos os resultados um que tenha o componente 'route' (rua)
                        for result in data["results"]:
                            # Se o próprio tipo do resultado for 'plus_code', ignora
                            if "plus_code" in result.get("types", []):
                                continue
                            
                            for component in result.get("address_components", []):
                                if "route" in component.get("types", []):
                                    google_name = component["long_name"]
                                    break
                            if google_name:
                                break
                        
                        # 2. Se não achou 'route', pega o primeiro formatted_address que não seja plus code
                        if not google_name:
                            for result in data["results"]:
                                if "plus_code" in result.get("types", []):
                                    continue
                                formatted = result.get("formatted_address")
                                if formatted and "+" not in formatted:
                                    google_name = formatted.split(",")[0]
                                    break
                                    
                        if google_name and google_name.strip():
                            google_name = google_name.strip()
                            try:
                                await db["ruas_customizadas"].insert_one({
                                    "coordenada": {
                                        "type": "Point",
                                        "coordinates": [snapped_lon, snapped_lat]
                                    },
                                    "nome_rua": google_name,
                                    "criado_em": datetime.now(timezone.utc)
                                })
                            except Exception as db_err:
                                print("Erro ao cadastrar rua no MongoDB:", db_err)
                            return google_name
        except Exception as e:
            print("Erro ao obter rua via Google Maps:", e)

    # 4. Fallback final Nominatim reverse
    headers = {"User-Agent": "SuaJornadaApp/1.0 (claus@example.com)"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers=headers,
                timeout=2.0
            )
            if r.status_code == 200:
                data = r.json()
                address = data.get("address", {})
                road = address.get("road") or address.get("suburb") or address.get("city")
                if road:
                    return road
                display_name = data.get("display_name")
                if display_name:
                    return display_name.split(",")[0]
        except Exception:
            pass

    return "Rua não identificada"


@router.post("", response_model=HistoricoGPS, status_code=201)
async def registrar_ponto_gps(
    dados: HistoricoGPSCreate,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Recebido pelo app mobile a cada 15 segundos durante a jornada."""
    mot_id = ObjectId(str(dados.motorista_id))
    j_id = dados.jornada_id
    coords = dados.localizacao.coordinates  # [longitude, latitude]
    
    # Tenta obter o nome da rua via OSRM nearest com fallback geoespacial para Google Maps e cache no MongoDB
    rua = "Rua não identificada"
    try:
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            rua = await obter_rua_por_coordenadas(lat, lon, db)
    except Exception as e:
        print("Erro ao obter rua:", e)

    ts = dados.timestamp or datetime.now(timezone.utc)
    
    # Tenta mesclar o ponto com o anterior se for muito próximo ou parado
    if len(coords) >= 2:
        mesclado_id = await tentar_mesclar_ponto_gps(
            db=db,
            motorista_id=mot_id,
            jornada_id=j_id,
            timestamp=ts,
            coords_lon=coords[0],
            coords_lat=coords[1],
            distancia_ultima_m=dados.distancia_ultima_m,
            status=dados.status,
            rua=rua
        )
        if mesclado_id:
            criado = await db["historico_gps"].find_one({"_id": mesclado_id})
            return HistoricoGPS(**criado)

    # Atualiza localizacao_atual da jornada ativa e envia evento SSE
    if len(coords) >= 2:
        lon, lat = coords[0], coords[1]
        try:
            await db["jornadas"].update_one(
                {"_id": j_id},
                {"$set": {
                    "localizacao_atual": {"lat": lat, "lon": lon},
                    "telemetria_status": dados.status or "CONDUZINDO",
                    "telemetria_ultima_atualizacao": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
                }}
            )
            from app.routers.events import event_manager
            await event_manager.broadcast("gps_atualizado", {
                "jornada_id": j_id,
                "motorista_id": str(mot_id),
                "lat": lat,
                "lon": lon,
                "status": dados.status
            })
        except Exception as e:
            print("Erro ao atualizar localizacao_atual:", e)

    doc = dados.model_dump()
    doc["motorista_id"] = mot_id
    doc["timestamp"] = ts
    doc["rua"] = rua
    doc["contador_mesclados"] = 1

    resultado = await db["historico_gps"].insert_one(doc)
    criado = await db["historico_gps"].find_one({"_id": resultado.inserted_id})
    return HistoricoGPS(**criado)


def decode_polyline(polyline_str: str) -> List[List[float]]:
    """
    Decodes a Polyline string into a list of [longitude, latitude] coordinates.
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    
    while index < len(polyline_str):
        shift, result = 0, 0
        while True:
            char = ord(polyline_str[index]) - 63
            index += 1
            result |= (char & 0x1f) << shift
            shift += 5
            if not (char & 0x20):
                break
        
        delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += delta_lat
        
        shift, result = 0, 0
        while True:
            char = ord(polyline_str[index]) - 63
            index += 1
            result |= (char & 0x1f) << shift
            shift += 5
            if not (char & 0x20):
                break
        
        delta_lng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += delta_lng
        
        coordinates.append([lng / 100000.0, lat / 100000.0])
        
    return coordinates


async def carregar_historico_compactado(url: str) -> list:
    from app.routers.uploads import MINIO_CLIENT, MINIO_BUCKET, MINIO_ENABLED, UPLOAD_DIR
    import gzip
    import io
    import json
    
    content = None
    if url.startswith("/static/uploads/"):
        filename = url.split("/")[-1]
        filepath = UPLOAD_DIR / "telemetria" / filename
        if filepath.exists():
            content = filepath.read_bytes()
        else:
            raise FileNotFoundError("Arquivo de telemetria não encontrado localmente")
    else:
        if MINIO_ENABLED and MINIO_CLIENT:
            parts = url.strip("/").split("/")
            if len(parts) >= 3:
                object_name = "/".join(parts[1:])
                response = MINIO_CLIENT.get_object(MINIO_BUCKET, object_name)
                try:
                    content = response.read()
                finally:
                    response.close()
                    response.release_conn()
            else:
                raise ValueError("URL do MinIO inválida")
        else:
            raise RuntimeError("MinIO não configurado e URL não é local")
            
    if not content:
        raise ValueError("Conteúdo da telemetria está vazio")
        
    with gzip.GzipFile(fileobj=io.BytesIO(content), mode="rb") as f:
        decompressed_data = f.read()
        
    return json.loads(decompressed_data.decode("utf-8"))


@router.post("/batch", status_code=201)
async def registrar_pontos_gps_batch(
    dados: HistoricoGPSBatch,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Recebido pelo app mobile contendo pontos de GPS em lote."""
    # Ordena os pontos cronologicamente para garantir processamento correto
    pontos_ordenados = sorted(dados.pontos, key=lambda x: x.timestamp)
    
    mot_id = ObjectId(str(dados.motorista_id))
    j_id = dados.jornada_id
    
    # Para otimizar chamadas de API, resolvemos apenas o último ponto e propagamos a rua
    rua = "Rua não identificada"
    if pontos_ordenados:
        ultimo = pontos_ordenados[-1]
        try:
            coords = ultimo.localizacao.coordinates
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
                rua = await obter_rua_por_coordenadas(lat, lon, db)
                
                # Atualiza a localização em tempo real da jornada ativa
                await db["jornadas"].update_one(
                    {"_id": j_id},
                    {"$set": {
                        "localizacao_atual": {"lat": lat, "lon": lon},
                        "telemetria_status": ultimo.status or "CONDUZINDO",
                    }}
                )
                from app.routers.events import event_manager
                await event_manager.broadcast("gps_atualizado", {
                    "jornada_id": j_id,
                    "motorista_id": str(mot_id),
                    "lat": lat,
                    "lon": lon,
                    "status": ultimo.status
                })
        except Exception as e:
            print("Erro ao atualizar localizacao_atual no batch:", e)

    contador_novos = 0
    contador_mesclados = 0
    
    for p in pontos_ordenados:
        coords = p.localizacao.coordinates
        if len(coords) < 2:
            continue
            
        mesclado_id = await tentar_mesclar_ponto_gps(
            db=db,
            motorista_id=mot_id,
            jornada_id=j_id,
            timestamp=p.timestamp,
            coords_lon=coords[0],
            coords_lat=coords[1],
            distancia_ultima_m=p.distancia_ultima_m,
            status=p.status,
            rua=rua
        )
        
        if mesclado_id:
            contador_mesclados += 1
        else:
            doc = {
                "motorista_id": mot_id,
                "jornada_id": j_id,
                "timestamp": p.timestamp,
                "localizacao": p.localizacao.model_dump(),
                "distancia_ultima_m": p.distancia_ultima_m,
                "status": p.status,
                "rua": rua,
                "contador_mesclados": 1
            }
            await db["historico_gps"].insert_one(doc)
            contador_novos += 1
            
    return {
        "status": "ok",
        "pontos_inseridos": contador_novos,
        "pontos_mesclados": contador_mesclados
    }



@router.get("/motorista/{motorista_id}", response_model=List[HistoricoGPS])
async def historico_motorista(
    motorista_id: str,
    jornada_id: Optional[str] = None,
    limite: int = 100000,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # 1. Se a jornada_id for fornecida, verifica se ela possui telemetria compactada salva
    if jornada_id:
        try:
            q_j = {"$or": [{"_id": jornada_id}, {"_id": ObjectId(jornada_id)}]}
        except Exception:
            q_j = {"_id": jornada_id}
            
        jornada = await db["jornadas"].find_one(q_j)
        if jornada and (jornada.get("telemetria_url") or jornada.get("status") == "ENCERRADA"):
            url = jornada.get("telemetria_url")
            if url:
                try:
                    pontos = await carregar_historico_compactado(url)
                    pontos.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
                    res = []
                    for p in pontos[:limite]:
                        res.append(HistoricoGPS(
                            timestamp=datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")),
                            motorista_id=ObjectId(motorista_id),
                            jornada_id=jornada_id,
                            localizacao=GeoPoint(type="Point", coordinates=[p["lon"], p["lat"]]),
                            distancia_ultima_m=p.get("distancia_ultima_m"),
                            status=p.get("status"),
                            rua=p.get("rua")
                        ))
                    return res
                except Exception as e:
                    print("Erro ao carregar telemetria compactada:", e)

    filtro: dict = {"motorista_id": ObjectId(motorista_id)}
    if jornada_id:
        filtro["jornada_id"] = jornada_id

    docs = await db["historico_gps"].find(filtro).sort("timestamp", -1).to_list(limite)
    return [HistoricoGPS(**d) for d in docs]


async def interpolar_lacunas_com_osrm(coords_raw: list) -> list:
    """
    Dada uma lista de coordenadas [[lon, lat], ...], detecta lacunas maiores que 80m
    e interpola via OSRM/driving para seguir a rota mais lógica pelas ruas.
    """
    if len(coords_raw) < 2:
        return coords_raw
        
    coords_interpoladas = []
    
    for i in range(len(coords_raw) - 1):
        pt1 = coords_raw[i]
        pt2 = coords_raw[i+1]
        coords_interpoladas.append(pt1)
        
        lon1, lat1 = pt1[0], pt1[1]
        lon2, lat2 = pt2[0], pt2[1]
        
        dist_m = calcular_distancia_m(lat1, lon1, lat2, lon2)
        
        # Se houver lacuna superior a 80 metros, calcula rota pelas ruas via OSRM
        if dist_m > 80.0:
            try:
                url = f"{settings.OSRM_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=1.5)
                    if resp.status_code == 200:
                        data = resp.json()
                        routes = data.get("routes", [])
                        if routes and "geometry" in routes[0]:
                            geom_coords = routes[0]["geometry"].get("coordinates", [])
                            if len(geom_coords) > 2:
                                for sub_pt in geom_coords[1:-1]:
                                    coords_interpoladas.append([sub_pt[0], sub_pt[1]])
            except Exception as e:
                print("Erro na interpolação OSRM de lacuna:", e)

    coords_interpoladas.append(coords_raw[-1])
    return coords_interpoladas


def _safe_float(val) -> float:
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


@router.get("/motorista/{motorista_id}/rota-ajustada")
async def rota_ajustada_motorista(
    motorista_id: str,
    jornada_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Retorna a rota da jornada.
    Prioridade: 1) segmentos_rota compactados (OSRM), 2) rota_polyline, 3) historico_gps bruto com interpolação de lacunas OSRM.
    """
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    try:
        q_j = {"$or": [{"_id": jornada_id}, {"_id": ObjectId(jornada_id)}]}
    except Exception:
        q_j = {"_id": jornada_id}

    jornada = await db["jornadas"].find_one(q_j)

    pontos = await obter_pontos_jornada(jornada, db) if jornada else []

    # Extração Dinâmica da Base de Operações (Primeiro ponto GPS da Jornada)
    base_lat = -20.26548
    base_lon = -40.29589
    if pontos and len(pontos) > 0:
        primeiro = pontos[0]
        # Pega de 'lat'/'lon' ou de 'localizacao'
        p_lat = primeiro.get("lat") or primeiro.get("localizacao", {}).get("coordinates", [0, 0])[1]
        p_lon = primeiro.get("lon") or primeiro.get("localizacao", {}).get("coordinates", [0, 0])[0]
        if p_lat != 0 and p_lon != 0:
            base_lat = p_lat
            base_lon = p_lon
            
    base_coords = (base_lat, base_lon)

    km_rodados = _safe_float(jornada.get("km", {}).get("rodados") if jornada else 0.0)
    total_horas_seg = _safe_float(jornada.get("horario", {}).get("total_horas_segundos") if jornada else 0.0)
    comprovantes = jornada.get("faturamento", {}).get("comprovantes_processados", []) if jornada else []

    jornada_data = jornada.get("data") if jornada else None

    if pontos:
        classified_segments = await classificar_jornada_segmentos(pontos, comprovantes, base_coords, jornada_data)
        if classified_segments:
            return {
                "status": "ok",
                "snapped": True,
                "segmentos_rota": classified_segments,
                "coordinates": [],
                "base_operacoes": {"lat": base_lat, "lon": base_lon},
                "distance_m": km_rodados * 1000.0,
                "duration_s": total_horas_seg
            }

    # 2) Fallback: segmentos_rota compactados legados
    if jornada and jornada.get("segmentos_rota"):
        segmentos = jornada["segmentos_rota"]
        decoded_segments = []
        for seg in segmentos:
            try:
                decoded = decode_polyline(seg.get("polyline", ""))
                if len(decoded) >= 2:
                    is_prod = seg.get("is_produtivo", False)
                    decoded_segments.append({
                        "status": "produtivo" if is_prod else "improdutivo_contra_base",
                        "rotulo": "Corrida Produtiva" if is_prod else "Deslocamento Sem Corrida",
                        "cor": "#10b981" if is_prod else "#ef4444",
                        "coords": decoded
                    })
            except Exception:
                pass

        if len(decoded_segments) > 0:
            return {
                "status": "ok",
                "snapped": True,
                "segmentos_rota": decoded_segments,
                "coordinates": [],
                "base_operacoes": {"lat": base_lat, "lon": base_lon},
                "distance_m": km_rodados * 1000.0,
                "duration_s": total_horas_seg
            }

    # 2) Fallback: rota_polyline simples
    if jornada and jornada.get("rota_polyline"):
        polyline_str = jornada["rota_polyline"]
        coords = decode_polyline(polyline_str)
        if len(coords) >= 2:
            km_rodados = _safe_float(jornada.get("km", {}).get("rodados") if jornada else 0.0)
            total_horas_seg = _safe_float(jornada.get("horario", {}).get("total_horas_segundos") if jornada else 0.0)
            return {
                "status": "ok",
                "snapped": True,
                "coordinates": coords,
                "distance_m": km_rodados * 1000.0,
                "duration_s": total_horas_seg
            }

    # 3) Fallback: pontos do historico_gps com interpolação de lacunas OSRM
    filtro_gps = {"jornada_id": str(jornada_id)}
    pontos = await db["historico_gps"].find(filtro_gps).sort("timestamp", 1).to_list(100000)

    if len(pontos) >= 2:
        coords_raw = []
        for p in pontos:
            loc = p.get("localizacao", {})
            c = loc.get("coordinates")
            if c and len(c) >= 2:
                coords_raw.append([c[0], c[1]])
        if len(coords_raw) >= 2:
            coords = await interpolar_lacunas_com_osrm(coords_raw)
            km_rodados = _safe_float(jornada.get("km", {}).get("rodados") if jornada else 0.0)
            total_horas_seg = _safe_float(jornada.get("horario", {}).get("total_horas_segundos") if jornada else 0.0)
            return {
                "status": "ok",
                "snapped": True,
                "coordinates": coords,
                "distance_m": km_rodados * 1000.0,
                "duration_s": total_horas_seg
            }

    return {
        "status": "ok",
        "snapped": False,
        "coordinates": [],
        "distance_m": 0.0,
        "duration_s": 0
    }




    filtro = {
        "motorista_id": ObjectId(motorista_id),
        "jornada_id": jornada_id
    }
    pontos = await db["historico_gps"].find(filtro).sort("timestamp", 1).to_list(1000)

    if len(pontos) < 2:
        return {
            "status": "ok",
            "snapped": False,
            "coordinates": [[p["localizacao"]["coordinates"][0], p["localizacao"]["coordinates"][1]] for p in pontos if "localizacao" in p and "coordinates" in p["localizacao"]],
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    coordenadas = []
    for p in pontos:
        loc = p.get("localizacao", {})
        coords = loc.get("coordinates", [])
        if len(coords) >= 2:
            coordenadas.append(f"{coords[0]},{coords[1]}")

    if len(coordenadas) < 2:
        return {
            "status": "ok",
            "snapped": False,
            "coordinates": [],
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    coords_chunks = [coordenadas[i:i + 100] for i in range(0, len(coordenadas), 99)]

    snapped_coords = []
    total_distance = 0.0
    total_duration = 0.0

    async with httpx.AsyncClient() as client:
        for chunk in coords_chunks:
            if len(chunk) < 2:
                continue
            path_str = ";".join(chunk)
            url = f"{settings.OSRM_URL}/match/v1/driving/{path_str}?overview=full&geometries=geojson"
            try:
                r = await client.get(url, timeout=5.0)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("code") == "Ok":
                        for match in data.get("matchings", []):
                            geom = match.get("geometry", {})
                            if geom.get("type") == "LineString":
                                snapped_coords.extend(geom.get("coordinates", []))
                            total_distance += match.get("distance", 0.0)
                            total_duration += match.get("duration", 0.0)
            except Exception:
                pass

    if not snapped_coords:
        fallback_coords = []
        for p in pontos:
            loc = p.get("localizacao", {})
            coords = loc.get("coordinates", [])
            if len(coords) >= 2:
                fallback_coords.append([coords[0], coords[1]])
        return {
            "status": "fallback",
            "snapped": False,
            "coordinates": fallback_coords,
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    return {
        "status": "ok",
        "snapped": True,
        "coordinates": snapped_coords,
        "distance_m": total_distance,
        "duration_s": total_duration
    }


@router.get("/alertas-inatividade")
async def obter_alertas_inatividade(
    db=Depends(get_db),
    current_user: UserPublic = Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    """
    Lista alertas de inatividade para motoristas com jornadas ativas.
    """
    jornadas_ativas = await db["jornadas"].find({
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO"]}
    }).to_list(100)

    alertas = []
    now = datetime.now(timezone.utc)

    for j in jornadas_ativas:
        motorista_id = j.get("motorista_id")
        if not motorista_id:
            continue

        user = await db["users"].find_one({"_id": motorista_id})
        limiar = MINUTOS_INATIVIDADE_ALERTA
        if user and "perfil_motorista" in user and user["perfil_motorista"]:
            limiar = user["perfil_motorista"].get("limiar_inatividade_minutos", MINUTOS_INATIVIDADE_ALERTA)

        pontos = await db["historico_gps"].find({
            "jornada_id": j["_id"]
        }).sort("timestamp", -1).to_list(100)

        if not pontos:
            continue

        ultimo_movimento_idx = None
        for idx, p in enumerate(pontos):
            dist = p.get("distancia_ultima_m") or 0.0
            if dist >= LIMIAR_PARADO_M:
                ultimo_movimento_idx = idx
                break

        if ultimo_movimento_idx is None:
            primeiro_parado = pontos[-1]
        elif ultimo_movimento_idx == 0:
            continue
        else:
            primeiro_parado = pontos[ultimo_movimento_idx - 1]

        ts_inicio_parado = primeiro_parado["timestamp"]
        if ts_inicio_parado.tzinfo is None:
            ts_inicio_parado = ts_inicio_parado.replace(tzinfo=timezone.utc)

        delta_segundos = (now - ts_inicio_parado).total_seconds()
        delta_minutos = int(delta_segundos / 60)

        if delta_minutos >= limiar:
            coords = pontos[0]["localizacao"]["coordinates"]
            lon, lat = coords[0], coords[1]
            rua = pontos[0].get("rua", "Desconhecido")
            pos_str = f"Lat: {lat:.4f}, Lon: {lon:.4f} ({rua})"

            minutos_parado = delta_minutos
            if delta_minutos == limiar + 1:
                minutos_parado = limiar

            alertas.append({
                "motorista_id": str(motorista_id),
                "motorista_nome": user.get("nome") if user else "Desconhecido",
                "jornada_id": j["_id"],
                "minutos_parado": minutos_parado,
                "ultima_posicao": pos_str,
                "timestamp": pontos[0]["timestamp"].isoformat() if isinstance(pontos[0]["timestamp"], datetime) else pontos[0]["timestamp"]
            })

    return {
        "alertas": alertas,
        "total_alertas": len(alertas)
    }


@router.get("/geocoder")
async def geocoder(query: str):
    """
    Pesquisa coordenadas (lat, lon) a partir de um texto utilizando Google Places API
    com fallback para OpenStreetMap Nominatim.
    """
    if not query:
        return []

    # 1. Tenta utilizar a API do Google se configurada
    if settings.GOOGLE_API_KEY:
        google_params = {
            "query": query,
            "key": settings.GOOGLE_API_KEY,
            "language": "pt-BR"
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params=google_params,
                    timeout=5.0
                )
                if r.status_code == 200:
                    data = r.json()
                    status = data.get("status")
                    if status in ("OK", "ZERO_RESULTS"):
                        results = []
                        for item in data.get("results", []):
                            lat = item.get("geometry", {}).get("location", {}).get("lat")
                            lon = item.get("geometry", {}).get("location", {}).get("lng")
                            name = item.get("name", "")
                            addr = item.get("formatted_address", "")
                            display_name = f"{name}, {addr}" if name and name not in addr else addr
                            if lat is not None and lon is not None:
                                results.append({
                                    "display_name": display_name,
                                    "lat": float(lat),
                                    "lon": float(lon)
                                })
                        return results
            except Exception as e:
                print("Erro no geocoder Google:", e)

    # 2. Fallback para OpenStreetMap Nominatim
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "SuaJornadaApp/1.0 (claus@example.com)"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                results = []
                for item in data:
                    results.append({
                        "display_name": item.get("display_name"),
                        "lat": float(item.get("lat")),
                        "lon": float(item.get("lon"))
                    })
                return results
        except Exception as e:
            print("Erro no geocoder Nominatim:", e)
            
    return []


def traduzir_passos_osrm(route_data) -> list:
    steps_res = []
    try:
        if "legs" in route_data and route_data["legs"]:
            leg = route_data["legs"][0]
            if "steps" in leg and leg["steps"]:
                for step in leg["steps"]:
                    maneuver = step.get("maneuver", {})
                    m_type = maneuver.get("type", "turn")
                    m_modifier = maneuver.get("modifier", "straight")
                    location = maneuver.get("location", [0.0, 0.0])
                    street_name = step.get("name", "").strip()
                    distance = step.get("distance", 0.0)
                    
                    rua = f"na {street_name}" if street_name else "em frente"
                    
                    traducoes_modifier = {
                        "left": "à esquerda",
                        "right": "à direita",
                        "sharp left": "acentuada à esquerda",
                        "sharp right": "acentuada à direita",
                        "slight left": "levemente à esquerda",
                        "slight right": "levemente à direita",
                        "straight": "em frente",
                        "uturn": "retorne"
                    }
                    mod = traducoes_modifier.get(m_modifier, "")
                    
                    if m_type == "depart":
                        instruction = f"Inicie a viagem {rua}"
                    elif m_type == "arrive":
                        instruction = "Você chegou ao seu destino"
                    elif m_type in ("turn", "new name", "fork"):
                        if mod:
                            instruction = f"Vire {mod} {rua}"
                        else:
                            instruction = f"Siga {rua}"
                    elif m_type == "roundabout":
                        instruction = f"Na rotatória, pegue a saída {rua}"
                    else:
                        instruction = f"Siga {rua}"
                        
                    steps_res.append({
                        "instruction": instruction,
                        "street": street_name,
                        "distance": distance,
                        "lat": location[1],
                        "lon": location[0],
                        "type": m_type,
                        "modifier": m_modifier
                    })
    except Exception as e:
        print("Erro ao traduzir passos OSRM:", e)
    return steps_res


@router.get("/calcular-rota")
async def calcular_rota(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float):
    """
    Consulta o OSRM local para calcular a distância, tempo estimado e geometria da rota.
    Com fallback automático para o OSRM público mundial se o local falhar/der timeout.
    """
    url = f"{settings.OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=geojson&steps=true"
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=4.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_km = route.get("distance", 0.0) / 1000.0
                    duration_minutes = route.get("duration", 0.0) / 60.0
                    geometry = route.get("geometry", {})
                    steps = traduzir_passos_osrm(route)
                    
                    return {
                        "distance_km": distance_km,
                        "duration_minutes": duration_minutes,
                        "geometry": geometry,
                        "steps": steps
                    }
        except Exception as e:
            print("Erro no OSRM local, tentando fallback para OSRM público:", e)

        # Fallback para o OSRM público mundial
        try:
            public_url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=geojson&steps=true"
            r = await client.get(public_url, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_km = route.get("distance", 0.0) / 1000.0
                    duration_minutes = route.get("duration", 0.0) / 60.0
                    geometry = route.get("geometry", {})
                    steps = traduzir_passos_osrm(route)
                    
                    return {
                        "distance_km": distance_km,
                        "duration_minutes": duration_minutes,
                        "geometry": geometry,
                        "steps": steps
                    }
        except Exception as ex:
            print("Erro no OSRM público calcular_rota:", ex)
            
    raise HTTPException(status_code=500, detail="Não foi possível calcular a rota com o OSRM local nem com o público.")


@router.get("/reverse")
async def reverse_geocode(
    lat: float,
    lon: float,
    db=Depends(get_db),
):
    """
    Obtém o nome da rua ou local a partir de coordenadas lat e lon.
    """
    # 1. Tenta obter a rua com nossa função inteligente de fallback + cache
    nome_rua = await obter_rua_por_coordenadas(lat, lon, db)
    if nome_rua and nome_rua != "Rua não identificada":
        return {"display_name": nome_rua, "lat": lat, "lon": lon}

    # 2. Fallback Nominatim reverse completo para pegar o display_name se não achar nada
    headers = {"User-Agent": "SuaJornadaApp/1.0 (claus@example.com)"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers=headers,
                timeout=3.0
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "display_name": data.get("display_name"),
                    "lat": lat,
                    "lon": lon
                }
        except Exception:
            pass

    return {"display_name": f"Localização em {lat:.5f}, {lon:.5f}", "lat": lat, "lon": lon}


@router.get("/resolver-maps")
async def resolver_maps(url: str):
    """
    Resolve links do Google Maps (curto ou longo) ou coordenadas brancas e extrai lat, lon e endereço.
    """
    import re
    from urllib.parse import unquote

    if not url:
        raise HTTPException(status_code=400, detail="URL inválida")

    # Extrai URL se for texto livre
    url_match = re.search(r'(https?://\S+)', url)
    url_to_resolve = url_match.group(1) if url_match else url

    # Verifica se são coordenadas diretas "-20.123,-40.123"
    coords_match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', url_to_resolve)
    if coords_match:
        lat = float(coords_match.group(1))
        lon = float(coords_match.group(2))
        rev = await reverse_geocode(lat, lon)
        return rev

    resolved_url = url_to_resolve
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.head(url_to_resolve, timeout=5.0)
            resolved_url = str(resp.url)
    except Exception:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url_to_resolve, timeout=5.0)
                resolved_url = str(resp.url)
        except Exception as e:
            print("Erro ao resolver URL:", e)

    lat, lon = None, None
    at_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', resolved_url)
    if at_match:
        lat = float(at_match.group(1))
        lon = float(at_match.group(2))
    else:
        q_match = re.search(r'[?&](?:q|query)=(-?\d+\.\d+),(-?\d+\.\d+)', resolved_url)
        if q_match:
            lat = float(q_match.group(1))
            lon = float(q_match.group(2))
        else:
            ll_match = re.search(r'[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)', resolved_url)
            if ll_match:
                lat = float(ll_match.group(1))
                lon = float(ll_match.group(2))

    place_match = re.search(r'/place/([^/]+)', resolved_url)
    display_name = "Localização Compartilhada"
    if place_match:
        display_name = unquote(place_match.group(1)).replace('+', ' ')

    if lat is not None and lon is not None:
        if display_name == "Localização Compartilhada":
            rev = await reverse_geocode(lat, lon)
            display_name = rev.get("display_name") or display_name
        return {
            "display_name": display_name,
            "lat": lat,
            "lon": lon
        }

    if place_match:
        search_query = unquote(place_match.group(1)).replace('+', ' ')
        results = await geocoder(search_query)
        if results:
            return results[0]

    raise HTTPException(status_code=400, detail="Não foi possível extrair coordenadas deste link.")


@router.post("/atualizar-destino")
async def atualizar_destino(
    jornada_id: str,
    lat: float,
    lon: float,
    endereco: str,
    db=Depends(get_db)
):
    """
    Grava o destino temporário na jornada e, se houver corrida particular em andamento, atualiza-a.
    """
    try:
        query = {"$or": [{"_id": jornada_id}, {"_id": ObjectId(jornada_id)}]}
    except Exception:
        query = {"_id": jornada_id}

    jornada = await db["jornadas"].find_one(query)
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    temp_destino = {
        "endereco": endereco,
        "lat": lat,
        "lon": lon
    }

    corridas = jornada.get("corridas_particulares", [])
    active_idx = None
    for idx, c in enumerate(corridas):
        if c.get("status") == "EM_ANDAMENTO":
            active_idx = idx
            break

    update_fields = {"temp_destino": temp_destino}
    if active_idx is not None:
        update_fields[f"corridas_particulares.{active_idx}.destino_endereco"] = endereco
        update_fields[f"corridas_particulares.{active_idx}.destino_coordenadas"] = {"lat": lat, "lon": lon}

    await db["jornadas"].update_one(query, {"$set": update_fields})
    return {"status": "ok", "temp_destino": temp_destino}


@router.get("/mapa-particular", response_class=HTMLResponse)
async def mapa_particular(
    origin_lat: float,
    origin_lon: float,
    destination_lat: Optional[float] = None,
    destination_lon: Optional[float] = None,
    jornada_id: Optional[str] = None
):
    """
    Retorna uma página HTML com mapa Leaflet escuro e interativo para localizar e definir destino.
    """
    dest_lat_js = destination_lat if destination_lat is not None else origin_lat
    dest_lon_js = destination_lon if destination_lon is not None else origin_lon
    has_dest_js = "true" if destination_lat is not None else "false"
    jId_str = jornada_id if jornada_id is not None else ""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mapa da Corrida Particular</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #0F172A; color: white; overflow: hidden; }}
            #map {{ width: 100%; height: 100%; z-index: 1; }}
            
            .search-container {{
                position: absolute;
                top: 16px;
                left: 16px;
                right: 16px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                background: rgba(30, 41, 59, 0.95);
                backdrop-filter: blur(8px);
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            .search-input-wrapper {{
                display: flex;
                align-items: center;
                padding: 12px 16px;
            }}
            .search-input-wrapper input {{
                flex: 1;
                background: transparent;
                border: none;
                color: white;
                font-size: 15px;
                outline: none;
            }}
            .search-input-wrapper input::placeholder {{ color: #94A3B8; }}
            .search-btn {{
                background: none;
                border: none;
                color: #38BDF8;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
            }}
            
            .suggestions-box {{
                max-height: 200px;
                overflow-y: auto;
                border-top: 1px solid rgba(255, 255, 255, 0.05);
                display: none;
            }}
            .suggestion-item {{
                padding: 12px 16px;
                font-size: 14px;
                color: #CBD5E1;
                cursor: pointer;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .suggestion-item:hover {{ background: rgba(255, 255, 255, 0.05); }}
            
            .info-card {{
                position: absolute;
                bottom: 24px;
                left: 16px;
                right: 16px;
                z-index: 1000;
                background: rgba(30, 41, 59, 0.95);
                backdrop-filter: blur(8px);
                border-radius: 16px;
                padding: 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            .info-title {{ font-size: 14px; font-weight: bold; color: #38BDF8; margin: 0; text-transform: uppercase; letter-spacing: 0.5px; }}
            .info-dest {{ font-size: 13px; color: #E2E8F0; margin: 0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
            .info-grid {{ display: flex; justify-content: space-between; font-size: 13px; color: #94A3B8; margin-top: 4px; }}
            .info-value {{ color: white; font-weight: 600; }}
            .price-highlight {{ font-size: 16px; font-weight: bold; color: #10B981; }}
            
            .btn-confirm {{
                width: 100%;
                background: #6366F1;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 8px;
                transition: background 0.2s;
            }}
            .btn-confirm:disabled {{ background: #475569; color: #94A3B8; cursor: not-allowed; }}
            .btn-confirm:not(:disabled):hover {{ background: #4F46E5; }}
            
            .success-overlay {{
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: #0F172A;
                z-index: 9999;
                display: none;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                gap: 16px;
                padding: 24px;
                text-align: center;
            }}
            .success-icon {{ font-size: 48px; color: #10B981; }}
            .success-title {{ font-size: 20px; font-weight: bold; }}
            .success-text {{ font-size: 14px; color: #94A3B8; }}
            .success-btn {{ background: #10B981; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="search-container">
            <div class="search-input-wrapper">
                <input type="text" id="search-input" placeholder="Pesquisar endereço de destino..." autocomplete="off">
                <button class="search-btn" id="search-btn">Buscar</button>
            </div>
            <div id="suggestions" class="suggestions-box"></div>
        </div>

        <div id="map"></div>

        <div class="info-card">
            <h4 class="info-title">Rota Particular</h4>
            <p class="info-dest" id="info-dest-txt">Destino: Selecione tocando ou arrastando</p>
            <div class="info-grid">
                <span>Distância: <span class="info-value" id="dist-val">-- km</span></span>
                <span>Duração: <span class="info-value" id="dur-val">-- min</span></span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 4px;">
                <span style="font-size:13px; color:#94A3B8;">Preço Estimado:</span>
                <span class="price-highlight" id="price-val">--</span>
            </div>
            <button id="btn-confirm" class="btn-confirm" disabled>Confirmar Destino</button>
        </div>

        <div class="success-overlay" id="success-screen">
            <div class="success-icon">✓</div>
            <h2 class="success-title">Destino Confirmado!</h2>
            <p class="success-text">As informações de rota e valores estimados foram sincronizadas.</p>
            <button class="success-btn" onclick="window.close()">Voltar ao App</button>
        </div>

        <script>
            const originLat = {origin_lat};
            const originLon = {origin_lon};
            let destLat = {dest_lat_js};
            let destLon = {dest_lon_js};
            let hasDest = {has_dest_js};
            const jornadaId = "{jId_str}";

            let currentRouteLine = null;
            let currentDestName = "";

            // Inicializa mapa escuro premium
            const map = L.map('map', {{ zoomControl: false }}).setView([originLat, originLon], 14);
            L.control.zoom({{ position: 'bottomright' }}).addTo(map);

            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; CartoDB &copy; OpenStreetMap'
            }}).addTo(map);

            // Marcador de Origem (Verde)
            const originIcon = L.divIcon({{
                html: '<div style="background-color: #10B981; width: 14px; height: 14px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>',
                className: '',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }});
            L.marker([originLat, originLon], {{ icon: originIcon }}).addTo(map).bindPopup('Local de Partida');

            // Marcador de Destino (Vermelho/Teal)
            const destIcon = L.divIcon({{
                html: '<div style="background-color: #6366F1; width: 14px; height: 14px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>',
                className: '',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }});

            let destMarker = null;

            if (hasDest) {{
                createOrUpdateDestMarker(destLat, destLon);
                recalcularRota();
            }}

            // Clique no mapa para definir destino
            map.on('click', function(e) {{
                createOrUpdateDestMarker(e.latlng.lat, e.latlng.lng);
                recalcularRota();
            }});

            function createOrUpdateDestMarker(lat, lon) {{
                destLat = lat;
                destLon = lon;
                hasDest = true;
                
                if (destMarker) {{
                    destMarker.setLatLng([lat, lon]);
                }} else {{
                    destMarker = L.marker([lat, lon], {{ icon: destIcon, draggable: true }}).addTo(map);
                    destMarker.on('dragend', function() {{
                        const pos = destMarker.getLatLng();
                        destLat = pos.lat;
                        destLon = pos.lng;
                        recalcularRota();
                    }});
                }}
            }}

            // Busca de endereço
            const searchInput = document.getElementById('search-input');
            const searchBtn = document.getElementById('search-btn');
            const suggestionsBox = document.getElementById('suggestions');

            searchBtn.addEventListener('click', () => triggerSearch());
            searchInput.addEventListener('keypress', (e) => {{
                if (e.key === 'Enter') triggerSearch();
            }});

            function triggerSearch() {{
                const query = searchInput.value;
                if (!query.trim()) return;

                fetch(`/gps/geocoder?query=${{encodeURIComponent(query)}}`)
                    .then(res => res.json())
                    .then(data => {{
                        suggestionsBox.innerHTML = '';
                        if (data.length > 0) {{
                            suggestionsBox.style.display = 'block';
                            data.forEach(item => {{
                                const div = document.createElement('div');
                                div.className = 'suggestion-item';
                                div.innerText = item.display_name;
                                div.addEventListener('click', () => {{
                                    searchInput.value = item.display_name;
                                    suggestionsBox.style.display = 'none';
                                    createOrUpdateDestMarker(item.lat, item.lon);
                                    map.setView([item.lat, item.lon], 15);
                                    recalcularRota();
                                }});
                                suggestionsBox.appendChild(div);
                            }});
                        }} else {{
                            suggestionsBox.style.display = 'none';
                        }}
                    }});
            }}

            // Oculta sugestões ao clicar fora
            document.addEventListener('click', (e) => {{
                if (!e.target.closest('.search-container')) {{
                    suggestionsBox.style.display = 'none';
                }}
            }});

            function calculatePrice(distanceKm, durationMin) {{
                return fetch('/config/precos-particulares')
                    .then(res => res.json())
                    .then(bands => {{
                        const agora = new Date();
                        const horaMinutosStr = String(agora.getHours()).padStart(2, '0') + ':' + String(agora.getMinutes()).padStart(2, '0');
                        for (let faixa of bands) {{
                            const inicio = faixa.hora_inicio;
                            const fim = faixa.hora_fim;
                            let matches = false;
                            if (inicio <= fim) {{
                                matches = horaMinutosStr >= inicio && horaMinutosStr <= fim;
                            }} else {{
                                matches = horaMinutosStr >= inicio || horaMinutosStr <= fim;
                            }}
                            if (matches) {{
                                return (distanceKm * faixa.preco_km) + (durationMin * faixa.preco_minuto);
                            }}
                        }}
                        if (bands.length > 0) {{
                            return (distanceKm * bands[0].preco_km) + (durationMin * bands[0].preco_minuto);
                        }}
                        return (distanceKm * 2.5) + (durationMin * 0.5);
                    }})
                    .catch(() => {{
                        return (distanceKm * 2.5) + (durationMin * 0.5);
                    }});
            }}

            function recalcularRota() {{
                if (!hasDest) return;

                // 1. Obtém o endereço das coordenadas de destino (reverse)
                fetch(`/gps/reverse?lat=${{destLat}}&lon=${{destLon}}`)
                    .then(res => res.json())
                    .then(data => {{
                        currentDestName = data.display_name || `Lat: ${{destLat.toFixed(4)}}, Lon: ${{destLon.toFixed(4)}}`;
                        document.getElementById('info-dest-txt').innerText = `Destino: ${{currentDestName}}`;
                        document.getElementById('info-dest-txt').title = currentDestName;
                    }});

                // 2. Calcula rota OSRM
                fetch(`/gps/calcular-rota?origin_lat=${{originLat}}&origin_lon=${{originLon}}&destination_lat=${{destLat}}&destination_lon=${{destLon}}`)
                    .then(res => res.json())
                    .then(data => {{
                        if (data.distance_km !== undefined) {{
                            const dist = data.distance_km;
                            const dur = data.duration_minutes;

                            document.getElementById('dist-val').innerText = `${{dist.toFixed(2)}} km`;
                            document.getElementById('dur-val').innerText = `${{dur.toFixed(1)}} min`;

                            calculatePrice(dist, dur).then(price => {{
                                document.getElementById('price-val').innerText = `R$ ${{price.toFixed(2)}}`;
                            }});

                            document.getElementById('btn-confirm').disabled = false;

                            // Desenha trajeto
                            if (currentRouteLine) {{
                                map.removeLayer(currentRouteLine);
                            }}
                            if (data.geometry) {{
                                currentRouteLine = L.geoJSON(data.geometry, {{
                                    style: {{ color: '#6366F1', weight: 5, opacity: 0.8 }}
                                }}).addTo(map);
                                map.fitBounds(currentRouteLine.getBounds(), {{ padding: [50, 80] }});
                            }}
                        }}
                    }})
                    .catch(err => {{
                        console.error('Erro ao recalcular rota:', err);
                        document.getElementById('btn-confirm').disabled = true;
                    }});
            }}

            // Confirmação
            const btnConfirm = document.getElementById('btn-confirm');
            btnConfirm.addEventListener('click', () => {{
                if (!jornadaId) {{
                    alert('Erro: jornada_id não fornecido.');
                    return;
                }}
                btnConfirm.disabled = true;
                btnConfirm.innerText = 'Salvando...';

                fetch(`/gps/atualizar-destino?jornada_id=${{jornadaId}}&lat=${{destLat}}&lon=${{destLon}}&endereco=${{encodeURIComponent(currentDestName)}}`, {{
                    method: 'POST'
                }})
                .then(res => res.json())
                .then(data => {{
                    if (data.status === 'ok') {{
                        document.getElementById('success-screen').style.display = 'flex';
                    }} else {{
                        alert('Erro ao confirmar destino no servidor.');
                        btnConfirm.disabled = false;
                        btnConfirm.innerText = 'Confirmar Destino';
                    }}
                }})
                .catch(err => {{
                    console.error(err);
                    alert('Erro de conexão ao confirmar destino.');
                    btnConfirm.disabled = false;
                    btnConfirm.innerText = 'Confirmar Destino';
                }});
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.delete("/jornada/{jornada_id}")
async def deletar_telemetria_jornada(
    jornada_id: str,
    db=Depends(get_db),
):
    """
    Remove todos os pontos de telemetria de uma jornada específica (botão temporário).
    """
    try:
        from bson import ObjectId
        gps_query = {"$or": [{"jornada_id": jornada_id}]}
        if ObjectId.is_valid(jornada_id):
            gps_query["$or"].append({"jornada_id": ObjectId(jornada_id)})

        res = await db["historico_gps"].delete_many(gps_query)
        
        jornada_query = {"$or": [{"_id": jornada_id}]}
        if ObjectId.is_valid(jornada_id):
            jornada_query["$or"].append({"_id": ObjectId(jornada_id)})
            
        await db["jornadas"].delete_many(jornada_query)

        return {
            "status": "ok",
            "message": f"Removidos {res.deleted_count} pontos de GPS e a jornada {jornada_id}."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapa-calor")
async def obter_mapa_calor(
    periodo: str = "mensal",  # "diario", "semanal", "mensal"
    motorista_id: Optional[str] = None,
    data_referencia: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    from datetime import date, timedelta, datetime, timezone
    now = datetime.now(timezone.utc)

    if data_referencia:
        try:
            ref_dt = datetime.strptime(data_referencia, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            ref_dt = now
    else:
        ref_dt = now

    if periodo == "diario":
        data_inicio = ref_dt.strftime("%Y-%m-%d")
        data_fim = data_inicio
    elif periodo == "semanal":
        dt_start = ref_dt - timedelta(days=ref_dt.weekday())
        dt_end = dt_start + timedelta(days=6)
        data_inicio = dt_start.strftime("%Y-%m-%d")
        data_fim = dt_end.strftime("%Y-%m-%d")
    else:  # mensal
        data_inicio = ref_dt.strftime("%Y-%m-01")
        data_fim = ref_dt.strftime("%Y-%m-31")

    query = {
        "data": {"$gte": data_inicio, "$lte": data_fim}
    }
    if motorista_id:
        query["$or"] = [{"motorista_id": motorista_id}]
        if ObjectId.is_valid(motorista_id):
            query["$or"].append({"motorista_id": ObjectId(motorista_id)})

    jornadas = await db["jornadas"].find(query).to_list(1000)

    pontos = []
    features = []
    total_valor = 0.0
    maior_ticket = 0.0

    def _normalizar_lat_lon(raw_lat, raw_lon):
        try:
            v1, v2 = float(raw_lat), float(raw_lon)
            if v1 == 0 or v2 == 0:
                return None, None
            # Se v1 for longitude (ex -40) e v2 latitude (ex -20), inverte
            if abs(v1) > 34.0 and abs(v2) <= 34.0:
                v1, v2 = v2, v1
            if -34.0 <= v1 <= 5.0 and -75.0 <= v2 <= -30.0:
                return v1, v2
        except Exception:
            pass
        return None, None

    for j in jornadas:
        j_data = j.get("data")
        # 1. Corridas Particulares
        for cp in j.get("corridas_particulares", []):
            loc_inicio = cp.get("localizacao_inicio") or {}
            raw_lat = loc_inicio.get("lat")
            raw_lon = loc_inicio.get("lon")
            lat, lon = _normalizar_lat_lon(raw_lat, raw_lon)
            valor = float(cp.get("valor_calculado") or 0.0)

            if lat and lon:
                total_valor += valor
                if valor > maior_ticket:
                    maior_ticket = valor

                p_item = {
                    "lat": float(lat),
                    "lon": float(lon),
                    "valor": round(valor, 2),
                    "plataforma": "PARTICULAR",
                    "tipo": cp.get("tipo_corrida") or "NORMAL",
                    "data": j_data
                }
                pontos.append(p_item)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": p_item
                })

        # 2. Comprovantes processados
        comprovantes = j.get("faturamento", {}).get("comprovantes_processados", [])
        segmentos = j.get("segmentos_rota", [])

        for c in comprovantes:
            valor = float(c.get("valor") or 0.0)
            plataforma = (c.get("plataforma") or "APP").upper()
            
            # Buscar coordenadas no segmento produtivo ou telemetria
            lat, lon = None, None
            if me := c.get("origemCoords"):
                lat, lon = me[0], me[1]
            elif me_list := c.get("coords"):
                if len(me_list) > 0:
                    lat, lon = me_list[0][0], me_list[0][1]

            if not lat and segmentos:
                for seg in segmentos:
                    if seg.get("is_produtivo") or seg.get("status") == "produtivo":
                        poly = seg.get("polyline", "")
                        if poly:
                            try:
                                decoded = decode_polyline(poly)
                                if decoded:
                                    lat, lon = decoded[0][0], decoded[0][1]
                                    break
                            except Exception:
                                pass

            lat, lon = _normalizar_lat_lon(lat, lon)
            if lat and lon:
                total_valor += valor
                if valor > maior_ticket:
                    maior_ticket = valor

                p_item = {
                    "lat": float(lat),
                    "lon": float(lon),
                    "valor": round(valor, 2),
                    "plataforma": plataforma,
                    "tipo": "APP",
                    "data": j_data
                }
                pontos.append(p_item)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lon), float(lat)]
                    },
                    "properties": p_item
                })

    qtd = len(pontos)
    ticket_medio = round(total_valor / qtd, 2) if qtd > 0 else 0.0

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return {
        "periodo": periodo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_pontos": qtd,
        "total_faturamento": round(total_valor, 2),
        "ticket_medio": ticket_medio,
        "maior_ticket": round(maior_ticket, 2),
        "pontos": pontos,
        "geojson": geojson
    }


