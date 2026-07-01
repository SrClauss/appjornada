import uuid
import zoneinfo
from datetime import date, datetime, timezone, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role, UserPublic
from app.models.jornada import (
    Jornada, JornadaCreate, JornadaUpdate,
    Pausa, Abastecimento, Sinistro,
)
from app.core.dependencies import get_current_user, require_roles
from app.core.security import verificar_senha
from app.core.config import settings

router = APIRouter(prefix="/jornadas", tags=["jornadas"])

HORAS_DIARIAS_CLT = 8.0
HORAS_SEMANAIS_CLT = 44.0
HORAS_MENSAIS_CLT = 220.0


def _calcular_saldo_horas(segundos: Optional[int]) -> Optional[float]:
    if segundos is None:
        return None
    trabalhadas = segundos / 3600
    return round(trabalhadas - HORAS_DIARIAS_CLT, 2)


def encode_polyline(points: List[tuple]) -> str:
    """
    points: list of (lat, lon) tuples
    """
    result = []
    last_lat = 0
    last_lng = 0
    for lat, lng in points:
        lat_val = int(round(lat * 1e5))
        lng_val = int(round(lng * 1e5))
        
        delta_lat = lat_val - last_lat
        delta_lng = lng_val - last_lng
        
        last_lat = lat_val
        last_lng = lng_val
        
        for val in (delta_lat, delta_lng):
            val = ~(val << 1) if val < 0 else (val << 1)
            while val >= 0x20:
                result.append(chr((0x20 | (val & 0x1f)) + 63))
                val >>= 5
            result.append(chr(val + 63))
    return "".join(result)


async def salvar_historico_compactado(jornada_id: str, pontos: list) -> str:
    from app.routers.uploads import MINIO_CLIENT, MINIO_BUCKET, MINIO_ENABLED, UPLOAD_DIR
    import gzip
    import io
    import json
    
    dados_pontos = []
    for p in pontos:
        loc = p.get("localizacao", {})
        coords = loc.get("coordinates", [0.0, 0.0])
        dados_pontos.append({
            "timestamp": p["timestamp"].isoformat() if isinstance(p["timestamp"], datetime) else str(p["timestamp"]),
            "lat": coords[1],
            "lon": coords[0],
            "distancia_ultima_m": p.get("distancia_ultima_m"),
            "status": p.get("status"),
            "rua": p.get("rua")
        })
        
    json_bytes = json.dumps(dados_pontos, ensure_ascii=False).encode("utf-8")
    
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(json_bytes)
    gzip_bytes = out.getvalue()
    
    filename = f"{jornada_id}.json.gz"
    
    if MINIO_ENABLED and MINIO_CLIENT:
        object_name = f"telemetria/{filename}"
        stream = io.BytesIO(gzip_bytes)
        from app.routers.uploads import _ensure_minio_bucket
        _ensure_minio_bucket()
        MINIO_CLIENT.put_object(
            MINIO_BUCKET,
            object_name,
            stream,
            len(gzip_bytes),
            content_type="application/gzip"
        )
        return f"/{MINIO_BUCKET}/{object_name}"
    else:
        local_dir = UPLOAD_DIR / "telemetria"
        local_dir.mkdir(parents=True, exist_ok=True)
        filepath = local_dir / filename
        filepath.write_bytes(gzip_bytes)
        return f"/static/uploads/telemetria/{filename}"


def _normalizar_jornada(d: dict) -> dict:
    if not d:
        return d
    
    # Normaliza KM
    if "km" not in d or d["km"] is None:
        inicial = d.get("km_inicial")
        final = d.get("km_final")
        rodados = None
        if final is not None and inicial is not None:
            rodados = round(final - inicial, 1)
        d["km"] = {
            "inicial": inicial,
            "final": final,
            "rodados": rodados
        }
    
    # Normaliza Horário (inicio / fim)
    if "horario" not in d or d["horario"] is None:
        inicio = None
        fim = None
        eventos = d.get("eventos", [])
        if eventos:
            inicio_ev = next((e for e in eventos if e.get("tipo") == "INICIO_JORNADA"), eventos[0])
            fim_ev = next((e for e in reversed(eventos) if e.get("tipo") == "FIM_JORNADA"), eventos[-1])
            
            ts_inicio = inicio_ev.get("timestamp")
            ts_fim = fim_ev.get("timestamp")
            
            if isinstance(ts_inicio, datetime):
                inicio = ts_inicio.time().isoformat()
            elif isinstance(ts_inicio, str):
                try:
                    inicio = ts_inicio.split("T")[1][:8]
                except Exception:
                    pass
                    
            if isinstance(ts_fim, datetime):
                fim = ts_fim.time().isoformat()
            elif isinstance(ts_fim, str):
                try:
                    fim = ts_fim.split("T")[1][:8]
                except Exception:
                    pass
        d["horario"] = {
            "inicio": inicio,
            "fim": fim,
            "total_horas_segundos": None
        }
        
    return d


async def _populate_motorista_nome(doc: dict, db) -> dict:
    if not doc:
        return doc
    mid = doc.get("motorista_id")
    if mid:
        user = await db["users"].find_one({"_id": ObjectId(str(mid))})
        if user:
            doc["motorista_nome"] = user.get("nome")
    return doc


# ─── CRUD principal ──────────────────────────────────────────────────────────

@router.post("", response_model=Jornada, status_code=201)
async def abrir_jornada(
    dados: JornadaCreate,
    pin: str,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    # Motorista só pode abrir jornada para si mesmo
    if current_user.role == Role.MOTORISTA:
        dados.motorista_id = ObjectId(str(current_user.id))

    # Valida PIN contra o hash armazenado no usuário
    user_doc = await db["users"].find_one({"_id": ObjectId(str(current_user.id))})
    pin_hash = user_doc.get("pin_hash") if user_doc else None
    if pin_hash:
        if not verificar_senha(pin, pin_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="PIN incorreto",
            )

    # Verifica se já existe jornada aberta para este motorista hoje
    hoje = date.today().isoformat()
    aberta = await db["jornadas"].find_one({
        "motorista_id": ObjectId(str(dados.motorista_id)),
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]},
    })
    if aberta:
        # Idempotência para cliques duplos: se foi criada há menos de 15 segundos, retorna ela
        try:
            inicio_str = aberta.get("horario", {}).get("inicio")
            if inicio_str:
                dt_str = f"{aberta['data']}T{inicio_str}"
                if not dt_str.endswith("Z"):
                    dt_str += "Z"
                dt_inicio = datetime.fromisoformat(dt_str)
                now_utc = datetime.now(timezone.utc)
                seconds_diff = abs((now_utc - dt_inicio).total_seconds())
                if seconds_diff <= 15:
                    normalized = _normalizar_jornada(aberta)
                    await _populate_motorista_nome(normalized, db)
                    return Jornada(**normalized)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma jornada ativa para este motorista.",
        )

    doc = dados.model_dump()
    doc["motorista_id"] = ObjectId(str(dados.motorista_id))
    doc["data"] = hoje
    doc["status"] = "ABERTA"
    doc["pin"] = pin
    doc["pausas"] = []
    doc["abastecimentos"] = []
    doc["sinistros"] = []
    doc["jornada_diaria_clt"] = HORAS_DIARIAS_CLT
    doc["jornada_semanal_clt"] = HORAS_SEMANAIS_CLT
    doc["jornada_mensal_clt"] = HORAS_MENSAIS_CLT
    if localizacao_lat is not None and localizacao_lon is not None:
        doc["localizacao_inicial"] = {"lat": localizacao_lat, "lon": localizacao_lon}
    if doc.get("horario") is None:
        doc["horario"] = {}
    doc["horario"]["inicio"] = datetime.now(timezone.utc).time().isoformat()

    # Gera _id composto: {nome}-{placa}-{timestamp}
    ts = datetime.now().strftime("%d%m%Y%H%M%S")
    doc["_id"] = f"{current_user.nome}-{dados.veiculo_id}-{ts}"

    await db["jornadas"].insert_one(doc)
    criado = await db["jornadas"].find_one({"_id": doc["_id"]})
    normalized = _normalizar_jornada(criado)
    await _populate_motorista_nome(normalized, db)
    return Jornada(**normalized)


@router.get("/aberta", response_model=Optional[Jornada])
async def jornada_aberta(
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna a jornada aberta do motorista autenticado (ou null)."""
    motorista_id = ObjectId(str(current_user.id))
    doc = await db["jornadas"].find_one({
        "motorista_id": motorista_id,
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]},
    })
    if doc:
        normalized = _normalizar_jornada(doc)
        await _populate_motorista_nome(normalized, db)
        return Jornada(**normalized)
    return None


@router.get("", response_model=List[Jornada])
async def listar_jornadas(
    data: Optional[date] = None,
    motorista_id: Optional[str] = None,
    status_filtro: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    filtro: dict = {}
    if current_user.role == Role.MOTORISTA:
        filtro["motorista_id"] = ObjectId(str(current_user.id))
    elif motorista_id:
        filtro["motorista_id"] = ObjectId(motorista_id)

    if data:
        filtro["data"] = data.isoformat()
    if status_filtro:
        filtro["status"] = status_filtro

    limit = min(limit, 200)  # teto de segurança
    docs = await db["jornadas"].find(filtro).sort("data", -1).skip(skip).limit(limit).to_list(limit)

    # Get driver names in bulk
    mids = list(set(d["motorista_id"] for d in docs if "motorista_id" in d))
    motoristas = await db["users"].find({"_id": {"$in": mids}}).to_list(None)
    mot_map = {str(m["_id"]): m["nome"] for m in motoristas}

    normalized_docs = []
    for d in docs:
        d = _normalizar_jornada(d)
        d["motorista_nome"] = mot_map.get(str(d.get("motorista_id")), "Motorista Desconhecido")
        
        # Obter último status de telemetria GPS para jornadas ativas
        if d.get("status") in ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]:
            try:
                ponto_recente = await db["historico_gps"].find_one(
                    {"jornada_id": str(d.get("_id"))},
                    sort=[("timestamp", -1)]
                )
                if ponto_recente:
                    d["telemetria_status"] = ponto_recente.get("status")
                    d["telemetria_ultima_atualizacao"] = ponto_recente["timestamp"].isoformat() if isinstance(ponto_recente.get("timestamp"), datetime) else str(ponto_recente.get("timestamp"))
            except Exception as e:
                print("Erro ao obter telemetria em tempo real para monitor:", e)

        normalized_docs.append(d)

    return [Jornada(**d) for d in normalized_docs]


@router.get("/eventos", response_model=List[dict])
async def listar_todos_eventos(
    data: Optional[date] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    motorista_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    filt_jornada = {}
    filt_gps = {}
    if motorista_id:
        filt_jornada["motorista_id"] = ObjectId(motorista_id)
        filt_gps["motorista_id"] = ObjectId(motorista_id)

    # Resolve date range
    d_ini = data_inicio or data
    d_fim = data_fim or data

    if d_ini and d_fim:
        filt_jornada["data"] = {"$gte": d_ini.isoformat(), "$lte": d_fim.isoformat()}
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        start_local = datetime.combine(d_ini, time.min).replace(tzinfo=tz)
        end_local = datetime.combine(d_fim, time.max).replace(tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = end_local.astimezone(timezone.utc)
        
        filt_gps["$or"] = [
            {"timestamp": {"$gte": start_utc, "$lte": end_utc}},
            {"timestamp": {"$gte": start_utc.isoformat(), "$lte": end_utc.isoformat()}}
        ]
    elif d_ini:
        filt_jornada["data"] = {"$gte": d_ini.isoformat()}
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        start_utc = datetime.combine(d_ini, time.min).replace(tzinfo=tz).astimezone(timezone.utc)
        filt_gps["timestamp"] = {"$gte": start_utc}
    elif d_fim:
        filt_jornada["data"] = {"$lte": d_fim.isoformat()}
        tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
        end_utc = datetime.combine(d_fim, time.max).replace(tzinfo=tz).astimezone(timezone.utc)
        filt_gps["timestamp"] = {"$lte": end_utc}

    jornadas = await db["jornadas"].find(filt_jornada).to_list(None)
    
    if motorista_id:
        motoristas = await db["users"].find({"_id": ObjectId(motorista_id)}).to_list(None)
    else:
        motoristas = await db["users"].find({"role": "MOTORISTA"}).to_list(None)
        
    mot_map = {str(m["_id"]): m["nome"] for m in motoristas}
    j_veiculos = {str(j["_id"]): j.get("veiculo_id", "—") for j in jornadas}
    
    todos_eventos = []
    for j in jornadas:
        motorista_nome = j.get("motorista_nome") or mot_map.get(str(j.get("motorista_id")), "Motorista Desconhecido")
        veiculo_id = j.get("veiculo_id")
        jornada_id = j.get("_id")
        
        eventos = j.get("eventos", [])
        if not eventos:
            eventos = []
            
            # 1. INICIO_JORNADA
            inicio_time = j.get("horario", {}).get("inicio")
            if inicio_time:
                inicio_time_str = inicio_time.isoformat() if isinstance(inicio_time, time) else str(inicio_time)
                try:
                    dt_str = f"{j['data']}T{inicio_time_str}"
                    ts = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
                except Exception:
                    ts = j.get("created_at") or datetime.now(timezone.utc)
                
                eventos.append({
                    "tipo": "INICIO_JORNADA",
                    "timestamp": ts,
                    "km": j.get("km", {}).get("inicial") if isinstance(j.get("km"), dict) else j.get("km_inicial") or 0.0,
                    "lat": j.get("localizacao_inicial", {}).get("lat") if j.get("localizacao_inicial") else None,
                    "lon": j.get("localizacao_inicial", {}).get("lon") if j.get("localizacao_inicial") else None,
                })

            # 2. Pausas
            for p in j.get("pausas", []):
                p_inicio = p.get("inicio")
                if p_inicio:
                    p_inicio_str = p_inicio.isoformat() if isinstance(p_inicio, time) else str(p_inicio)
                    try:
                        ts_in = datetime.fromisoformat(f"{j['data']}T{p_inicio_str}").replace(tzinfo=timezone.utc)
                    except Exception:
                        ts_in = datetime.now(timezone.utc)
                    eventos.append({
                        "tipo": "INICIO_INTERVALO",
                        "timestamp": ts_in,
                        "km": p.get("km"),
                        "lat": p.get("localizacao_inicio", {}).get("lat") if p.get("localizacao_inicio") else None,
                        "lon": p.get("localizacao_inicio", {}).get("lon") if p.get("localizacao_inicio") else None,
                    })
                
                p_fim = p.get("fim")
                if p_fim:
                    p_fim_str = p_fim.isoformat() if isinstance(p_fim, time) else str(p_fim)
                    try:
                        ts_fi = datetime.fromisoformat(f"{j['data']}T{p_fim_str}").replace(tzinfo=timezone.utc)
                    except Exception:
                        ts_fi = datetime.now(timezone.utc)
                    eventos.append({
                        "tipo": "FIM_INTERVALO",
                        "timestamp": ts_fi,
                        "km": p.get("km"),
                        "lat": p.get("localizacao_fim", {}).get("lat") if p.get("localizacao_fim") else None,
                        "lon": p.get("localizacao_fim", {}).get("lon") if p.get("localizacao_fim") else None,
                    })

            # 3. Abastecimentos
            for ab in j.get("abastecimentos", []):
                ab_id = ab.get("id")
                ts_ab = None
                if ab_id:
                    try:
                        ts_ab = datetime.fromtimestamp(int(ab_id) / 1000, tz=timezone.utc)
                    except Exception:
                        pass
                if not ts_ab:
                    ab_inicio = ab.get("hora_inicio")
                    if ab_inicio:
                        ab_inicio_str = ab_inicio.isoformat() if isinstance(ab_inicio, time) else str(ab_inicio)
                        try:
                            ts_ab = datetime.fromisoformat(f"{j['data']}T{ab_inicio_str}").replace(tzinfo=timezone.utc)
                        except Exception:
                            pass
                if not ts_ab:
                    ts_ab = datetime.now(timezone.utc)
                
                eventos.append({
                    "tipo": "ABASTECIMENTO",
                    "timestamp": ts_ab,
                    "km": ab.get("km"),
                    "lat": ab.get("localizacao", {}).get("lat") if ab.get("localizacao") else None,
                    "lon": ab.get("localizacao", {}).get("lon") if ab.get("localizacao") else None,
                })

            # 4. FIM_JORNADA
            fim_time = j.get("horario", {}).get("fim")
            if fim_time:
                fim_time_str = fim_time.isoformat() if isinstance(fim_time, time) else str(fim_time)
                try:
                    dt_str = f"{j['data']}T{fim_time_str}"
                    ts = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
                except Exception:
                    ts = j.get("created_at") or datetime.now(timezone.utc)
                
                eventos.append({
                    "tipo": "FIM_JORNADA",
                    "timestamp": ts,
                    "km": j.get("km", {}).get("final") if isinstance(j.get("km"), dict) else j.get("km_final") or 0.0,
                    "lat": j.get("localizacao_final", {}).get("lat") if j.get("localizacao_final") else None,
                    "lon": j.get("localizacao_final", {}).get("lon") if j.get("localizacao_final") else None,
                })

        for ev in eventos:
            ev_ts = ev.get("timestamp")
            ev_lat = ev.get("lat")
            ev_lon = ev.get("lon")
            ev_rua = ev.get("rua")
            
            # Tenta buscar rua/localização do GPS histórico se faltar
            if not ev_lat or not ev_lon or not ev_rua:
                from datetime import timedelta
                pt = await db["historico_gps"].find_one({
                    "motorista_id": j.get("motorista_id"),
                    "timestamp": {"$gte": ev_ts - timedelta(minutes=10), "$lte": ev_ts + timedelta(minutes=10)}
                }, sort=[("timestamp", 1)])
                if pt:
                    if not ev_rua:
                        ev_rua = pt.get("rua")
                    coords = pt.get("localizacao", {}).get("coordinates", [])
                    if not ev_lat and len(coords) > 1:
                        ev_lat = coords[1]
                    if not ev_lon and len(coords) > 0:
                        ev_lon = coords[0]
            
            rua_str = f" | {ev_rua}" if ev_rua else ""
            detalhes = f"{ev.get('tipo')}{rua_str}"
            if ev_lat and ev_lon:
                detalhes += f" | Lat: {ev_lat}, Lon: {ev_lon}"
            if ev.get("km"):
                detalhes += f" | Km: {ev.get('km')}"

            todos_eventos.append({
                "jornada_id": str(jornada_id),
                "motorista_id": str(j.get("motorista_id")),
                "motorista_nome": motorista_nome,
                "veiculo_id": veiculo_id,
                "tipo": ev.get("tipo"),
                "timestamp": ev.get("timestamp"),
                "km": ev.get("km"),
                "rua": ev_rua,
                "lat": ev_lat,
                "lon": ev_lon,
                "detalhes": detalhes,
            })
            
    # Carrega pontos de telemetria GPS como eventos
    gps_limit = skip + limit
    gps_points = await db["historico_gps"].find(filt_gps).sort("timestamp", -1).limit(gps_limit).to_list(None)
    for pt in gps_points:
        m_id = str(pt.get("motorista_id"))
        j_id = str(pt.get("jornada_id")) if pt.get("jornada_id") else ""
        motorista_nome = mot_map.get(m_id, "Motorista Desconhecido")
        veiculo_id = j_veiculos.get(j_id, "—")
        
        coords = pt.get("localizacao", {}).get("coordinates", [])
        lat = coords[1] if len(coords) > 1 else None
        lon = coords[0] if len(coords) > 0 else None
        status_gps = pt.get("status", "TELEMETRIA")
        dist = pt.get("distancia_ultima_m", 0.0)
        rua = pt.get("rua")
        rua_str = f" | {rua}" if rua else ""
        
        ts = pt.get("timestamp")
        if isinstance(ts, datetime):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)
            
        todos_eventos.append({
            "jornada_id": j_id,
            "motorista_id": m_id,
            "motorista_nome": motorista_nome,
            "veiculo_id": veiculo_id,
            "tipo": "TELEMETRIA_GPS",
            "timestamp": ts_str,
            "km": None,
            "rua": rua,
            "lat": lat,
            "lon": lon,
            "detalhes": f"{status_gps}{rua_str} | Lat: {lat}, Lon: {lon} | Dist: {dist:.1f}m",
        })
            
    # Ordena decrescente por timestamp
    def get_timestamp(e):
        ts = e.get("timestamp")
        if isinstance(ts, datetime):
            return ts.isoformat()
        return str(ts) if ts else ""
        
    todos_eventos.sort(key=get_timestamp, reverse=True)
    return todos_eventos[skip : skip + limit]


@router.get("/{jornada_id}", response_model=Jornada)
async def get_jornada(
    jornada_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    if (
        current_user.role == Role.MOTORISTA
        and str(doc["motorista_id"]) != str(current_user.id)
    ):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    normalized = _normalizar_jornada(doc)
    await _populate_motorista_nome(normalized, db)
    return Jornada(**normalized)


@router.patch("/{jornada_id}", response_model=Jornada)
async def atualizar_jornada(
    jornada_id: str,
    dados: JornadaUpdate,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    update = dados.model_dump(exclude_none=True)
    await db["jornadas"].update_one({"_id": jornada_id}, {"$set": update})
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    
    normalized = _normalizar_jornada(atualizado)
    await _populate_motorista_nome(normalized, db)
    return Jornada(**normalized)


# ─── Fechar jornada ──────────────────────────────────────────────────────────

@router.patch("/{jornada_id}/fechar", response_model=Jornada)
async def fechar_jornada(
    jornada_id: str,
    km_final: float,
    faturamento_uber: float = 0.0,
    corridas_uber: int = 0,
    faturamento_99: float = 0.0,
    corridas_99: int = 0,
    faturamento_outros: float = 0.0,
    corridas_outros: int = 0,
    foto_km_final_url: Optional[str] = None,
    comprovante_uber_url: Optional[str] = None,
    comprovante_99_url: Optional[str] = None,
    comprovante_outros_url: Optional[str] = None,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    observacoes: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    if doc["status"] == "ENCERRADA":
        # Idempotência para cliques duplos: se foi encerrada muito recentemente, retorna ela
        try:
            fim_str = doc.get("horario", {}).get("fim")
            if fim_str:
                dt_str = f"{doc['data']}T{fim_str}"
                if not dt_str.endswith("Z"):
                    dt_str += "Z"
                dt_fim = datetime.fromisoformat(dt_str)
                now_utc = datetime.now(timezone.utc)
                seconds_diff = abs((now_utc - dt_fim).total_seconds())
                if seconds_diff <= 15:
                    return Jornada(**_normalizar_jornada(doc))
        except Exception:
            pass

        raise HTTPException(status_code=409, detail="Jornada já encerrada")
    if doc["status"] not in ("ABERTA", "EM_ANDAMENTO", "EM_PAUSA"):
        raise HTTPException(status_code=409, detail="Jornada em estado inválido para encerramento")

    fim = datetime.now(timezone.utc)
    inicio_str = doc.get("horario", {}).get("inicio")
    total_segundos = None
    if inicio_str:
        from datetime import time
        h, m, s = map(int, inicio_str.split(":")[:3])
        inicio_dt = datetime.combine(date.today(), time(h, m, s), tzinfo=timezone.utc)
        total_segundos = int((fim - inicio_dt).total_seconds())

    km_inicial = doc.get("km", {}).get("inicial") or 0
    km_rodados = round(km_final - km_inicial, 1)
    total_faturamento = faturamento_uber + faturamento_99 + faturamento_outros

    # Calcular bonus baseado no faturamento total e horario de inicio
    bonus_dia = 0.0
    try:
        from datetime import time as dt_time
        metas = await db["metas_bonus"].find().to_list(100)
        j_inicio_str = doc.get("horario", {}).get("inicio")
        j_time = None
        if j_inicio_str:
            parts = j_inicio_str.split(":")
            if len(parts) >= 2:
                h = int(parts[0])
                m = int(parts[1])
                s = int(parts[2].split(".")[0]) if len(parts) > 2 else 0
                j_time = dt_time(h, m, s)
            
        for meta in metas:
            fmin = meta.get("faixa_minima") or 0.0
            fmax = meta.get("faixa_maxima")
            if total_faturamento >= fmin and (fmax is None or total_faturamento <= fmax):
                h_ini_str = meta.get("hora_inicio")
                h_fim_str = meta.get("hora_fim")
                if h_ini_str and h_fim_str and j_time:
                    try:
                        ini_parts = h_ini_str.split(":")
                        h_ini = dt_time(int(ini_parts[0]), int(ini_parts[1]), int(ini_parts[2]) if len(ini_parts) > 2 else 0)
                        
                        fim_parts = h_fim_str.split(":")
                        h_fim = dt_time(int(fim_parts[0]), int(fim_parts[1]), int(fim_parts[2]) if len(fim_parts) > 2 else 0)
                        
                        if h_ini <= h_fim:
                            if not (h_ini <= j_time <= h_fim):
                                continue
                        else:
                            if not (j_time >= h_ini or j_time <= h_fim):
                                continue
                    except Exception as e_time:
                        print("Erro ao verificar faixa horaria:", e_time)
                        continue
                
                bonus_dia = max(bonus_dia, meta.get("bonus") or 0.0)
    except Exception as e:
        print("Erro ao calcular bonus no fechamento:", e)

    update = {
        "status": "ENCERRADA",
        "horario.fim": fim.time().isoformat(),
        "horario.total_horas_segundos": total_segundos,
        "km.final": km_final,
        "km.rodados": km_rodados,
        "faturamento.uber": faturamento_uber,
        "faturamento.noventa_nove": faturamento_99,
        "faturamento.outros": faturamento_outros,
        "faturamento.total_dia": total_faturamento,
        "faturamento.corridas_uber": corridas_uber,
        "faturamento.corridas_99": corridas_99,
        "faturamento.corridas_outros": corridas_outros,
        "saldo_horas_dia": _calcular_saldo_horas(total_segundos),
        "bonus_dia": bonus_dia,
    }
    # Registra localização final se fornecida
    if localizacao_lat is not None and localizacao_lon is not None:
        update["localizacao_final"] = {"lat": localizacao_lat, "lon": localizacao_lon}
    if foto_km_final_url:
        update["fotos.km_final_url"] = foto_km_final_url
    if comprovante_uber_url:
        update["faturamento.comprovante_uber_url"] = comprovante_uber_url
    if comprovante_99_url:
        update["faturamento.comprovante_99_url"] = comprovante_99_url
    if comprovante_outros_url:
        update["faturamento.comprovante_outros_url"] = comprovante_outros_url
    if observacoes:
        update["observacoes"] = observacoes

    # Compactação e limpeza de telemetria GPS histórica
    pontos = await db["historico_gps"].find({"jornada_id": jornada_id}).sort("timestamp", 1).to_list(100000)
    if pontos:
        coords_para_polyline = []
        for p in pontos:
            loc = p.get("localizacao", {})
            coords = loc.get("coordinates", [])
            if len(coords) >= 2:
                coords_para_polyline.append((coords[1], coords[0]))  # (lat, lon)
        
        if coords_para_polyline:
            try:
                update["rota_polyline"] = encode_polyline(coords_para_polyline)
            except Exception as e:
                print("Erro ao codificar polyline:", e)
                
        try:
            telemetria_url = await salvar_historico_compactado(jornada_id, pontos)
            update["telemetria_url"] = telemetria_url
        except Exception as e:
            print("Erro ao salvar telemetria compactada:", e)
            
        try:
            await db["historico_gps"].delete_many({"jornada_id": jornada_id})
        except Exception as e:
            print("Erro ao limpar historico_gps:", e)

    await db["jornadas"].update_one({"_id": jornada_id}, {"$set": update})
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    normalized = _normalizar_jornada(atualizado)
    await _populate_motorista_nome(normalized, db)
    return Jornada(**normalized)


# ─── Pausas ──────────────────────────────────────────────────────────────────

@router.post("/{jornada_id}/pausas", response_model=Jornada, status_code=201)
async def iniciar_pausa(
    jornada_id: str,
    tipo: str = "PAUSA_MOTORISTA",
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    # Verifica se já existe alguma pausa ativa (sem "fim")
    pausas = doc.get("pausas", [])
    if any(p.get("fim") is None for p in pausas):
        # Idempotência para cliques duplos: se já está em pausa, retorna
        return Jornada(**_normalizar_jornada(doc))

    pausa = {
        "id": uuid.uuid4().hex[:8],
        "tipo": tipo,
        "inicio": datetime.now(timezone.utc).time().isoformat(),
        "fim": None,
        "duracao_segundos": None,
        "localizacao_inicio": {"lat": localizacao_lat, "lon": localizacao_lon}
        if localizacao_lat else None,
        "localizacao_fim": None,
    }
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"pausas": pausa}, "$set": {"status": "EM_PAUSA"}},
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**_normalizar_jornada(atualizado))


@router.patch("/{jornada_id}/pausas/{pausa_id}/fechar", response_model=Jornada)
async def fechar_pausa(
    jornada_id: str,
    pausa_id: str,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    pausas = doc.get("pausas", [])
    pausa = next((p for p in pausas if p["id"] == pausa_id), None)
    if not pausa:
        raise HTTPException(status_code=404, detail="Pausa não encontrada")

    if pausa.get("fim") is not None:
        # Idempotência para cliques duplos: a pausa já foi fechada
        return Jornada(**_normalizar_jornada(doc))

    fim_time = datetime.now(timezone.utc).time()
    from datetime import time
    inicio_time = time.fromisoformat(pausa["inicio"])
    duracao = (
        datetime.combine(date.today(), fim_time)
        - datetime.combine(date.today(), inicio_time)
    ).seconds

    await db["jornadas"].update_one(
        {"_id": jornada_id, "pausas.id": pausa_id},
        {
            "$set": {
                "pausas.$.fim": fim_time.isoformat(),
                "pausas.$.duracao_segundos": duracao,
                "pausas.$.localizacao_fim": {"lat": localizacao_lat, "lon": localizacao_lon}
                if localizacao_lat else None,
                "status": "EM_ANDAMENTO",
            }
        },
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**_normalizar_jornada(atualizado))


# ─── Abastecimento ───────────────────────────────────────────────────────────

@router.post("/{jornada_id}/abastecimentos", response_model=Jornada, status_code=201)
async def registrar_abastecimento(
    jornada_id: str,
    dados: Abastecimento,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    # Verifica duplicidade pelo ID do abastecimento (idempotência para clique duplo)
    abastecimentos = doc.get("abastecimentos", [])
    if any(a.get("id") == dados.id for a in abastecimentos):
        return Jornada(**_normalizar_jornada(doc))

    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"abastecimentos": dados.model_dump()}},
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**_normalizar_jornada(atualizado))


# ─── Sinistro ────────────────────────────────────────────────────────────────

@router.post("/{jornada_id}/sinistros", response_model=Jornada, status_code=201)
async def registrar_sinistro(
    jornada_id: str,
    dados: Sinistro,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    # Verifica duplicidade pelo ID do sinistro (idempotência para clique duplo)
    sinistros = doc.get("sinistros", [])
    if any(s.get("id") == dados.id for s in sinistros):
        return Jornada(**_normalizar_jornada(doc))

    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"sinistros": dados.model_dump()}},
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**_normalizar_jornada(atualizado))


# ─── Dashboard CLT ───────────────────────────────────────────────────────────

@router.get("/{motorista_id}/resumo-clt", tags=["dashboard"])
async def resumo_clt(
    motorista_id: str,
    semana_inicio: date,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna horas trabalhadas, saldo e faturamento da semana."""
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    from datetime import timedelta
    semana_fim = semana_inicio + timedelta(days=6)

    docs = await db["jornadas"].find({
        "motorista_id": ObjectId(motorista_id),
        "data": {"$gte": semana_inicio.isoformat(), "$lte": semana_fim.isoformat()},
        "status": "ENCERRADA",
    }).to_list(7)

    total_segundos = sum(
        d.get("horario", {}).get("total_horas_segundos") or 0 for d in docs
    )
    total_horas = round(total_segundos / 3600, 2)
    saldo_semanal = round(total_horas - HORAS_SEMANAIS_CLT, 2)

    total_faturamento = sum(
        (d.get("faturamento") or {}).get("total_dia") or 0 for d in docs
    )

    return {
        "motorista_id": motorista_id,
        "semana_inicio": semana_inicio,
        "semana_fim": semana_fim,
        "dias_trabalhados": len(docs),
        "total_horas_trabalhadas": total_horas,
        "meta_semanal_horas": HORAS_SEMANAIS_CLT,
        "saldo_horas_semana": saldo_semanal,
        "faturamento_semana": total_faturamento,
        "status": "OK" if total_horas >= HORAS_SEMANAIS_CLT else "ABAIXO_DA_META",
    }


@router.get("/{motorista_id}/resumo-clt-mensal", tags=["dashboard"])
async def resumo_clt_mensal(
    motorista_id: str,
    ano: int,
    mes: int,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna horas trabalhadas, saldo e faturamento do mês."""
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    import calendar
    _, ultimo_dia = calendar.monthrange(ano, mes)
    mes_inicio = date(ano, mes, 1).isoformat()
    mes_fim = date(ano, mes, ultimo_dia).isoformat()

    docs = await db["jornadas"].find({
        "motorista_id": ObjectId(motorista_id),
        "data": {"$gte": mes_inicio, "$lte": mes_fim},
        "status": "ENCERRADA",
    }).to_list(31)

    total_segundos = sum(
        d.get("horario", {}).get("total_horas_segundos") or 0 for d in docs
    )
    total_horas = round(total_segundos / 3600, 2)
    saldo_mensal = round(total_horas - HORAS_MENSAIS_CLT, 2)
    total_faturamento = sum(
        (d.get("faturamento") or {}).get("total_dia") or 0 for d in docs
    )
    # Saldo acumulado por semana dentro do mês
    saldo_por_dia = [
        {
            "data": d.get("data"),
            "horas": round((d.get("horario", {}).get("total_horas_segundos") or 0) / 3600, 2),
            "saldo_dia": d.get("saldo_horas_dia"),
            "faturamento": (d.get("faturamento") or {}).get("total_dia") or 0,
        }
        for d in sorted(docs, key=lambda x: x.get("data", ""))
    ]

    return {
        "motorista_id": motorista_id,
        "mes": f"{ano}-{mes:02d}",
        "dias_trabalhados": len(docs),
        "total_horas_trabalhadas": total_horas,
        "meta_mensal_horas": HORAS_MENSAIS_CLT,
        "saldo_horas_mes": saldo_mensal,
        "faturamento_mes": total_faturamento,
        "status": "OK" if total_horas >= HORAS_MENSAIS_CLT else "ABAIXO_DA_META",
        "detalhe_por_dia": saldo_por_dia,
    }


@router.post("/aberta/comprovante", status_code=201)
async def upload_e_processar_comprovante(
    arquivo: UploadFile = File(...),
    plataforma: Optional[str] = Form(None),
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Recebe um print de faturamento do motorista, faz upload para o MinIO,
    usa o Gemini para analisar os dados (plataforma, valor, origem e destino)
    e atualiza a jornada aberta acumulando o valor e anexando o comprovante com localizações.
    """
    # Encontra a jornada ativa
    doc = await db["jornadas"].find_one({
        "motorista_id": ObjectId(str(current_user.id)),
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]}
    })
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma jornada ativa encontrada para este motorista."
        )

    # 1. Lê os bytes do arquivo para enviar ao Gemini
    conteudo = await arquivo.read()
    await arquivo.seek(0)

    # 2. Chama o Gemini para ler o print e identificar plataforma, valor e localizações
    import base64
    import httpx
    import json
    
    plataforma_final = "OUTROS"
    valor = 0.0
    origem = None
    destino = None
    data_hora = None

    try:
        base64_image = base64.b64encode(conteudo).decode('utf-8')
        import os
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        
        # Determina o MIME type correto para o Gemini
        mime_type = arquivo.content_type or "image/jpeg"
        if mime_type not in ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]:
            fn = (arquivo.filename or "").lower()
            if fn.endswith(".png"):
                mime_type = "image/png"
            elif fn.endswith(".webp"):
                mime_type = "image/webp"
            else:
                mime_type = "image/jpeg"

        prompt_plataforma = ""
        if plataforma:
            prompt_plataforma = f"O usuário informou que a plataforma deste print é: {plataforma.upper()}.\n"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Você é um assistente especializado em ler prints de faturamento ou de corridas de motoristas (Uber, 99 ou outros).\n"
                                "Extraia as seguintes informações do print de forma extremamente precisa:\n"
                                f"{prompt_plataforma}"
                                "1. Plataforma (UBER, 99 ou OUTROS)\n"
                                "2. Valor total da corrida ou do faturamento selecionado (represente como float, ex: 15.50)\n"
                                "3. Local de Origem / Partida (se visível)\n"
                                "4. Local de Destino / Chegada (se visível)\n"
                                "5. Data e hora da corrida (se visível)\n\n"
                                "Retorne estritamente um JSON no formato:\n"
                                "{\n"
                                "  \"plataforma\": \"UBER\" ou \"99\" ou \"OUTROS\",\n"
                                "  \"valor\": float,\n"
                                "  \"origem\": string ou null,\n"
                                "  \"destino\": string ou null,\n"
                                "  \"data_hora\": string ou null\n"
                                "}\n"
                                "Não retorne nenhuma marcação markdown ou texto explicativo, retorne apenas o JSON puro."
                            )
                        },
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as httpx_client:
            response = await httpx_client.post(url, json=payload)
            if response.status_code == 200:
                res_data = response.json()
                text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                if "```" in text_response:
                    text_response = text_response.split("```")[-2].replace("json", "").strip()
                parsed = json.loads(text_response)
                plataforma_final = plataforma.upper() if plataforma else parsed.get("plataforma", "OUTROS").upper()
                if plataforma_final not in ["UBER", "99", "OUTROS"]:
                    plataforma_final = "OUTROS"
                valor = float(parsed.get("valor", 0.0))
                origem = parsed.get("origem")
                destino = parsed.get("destino")
                data_hora = parsed.get("data_hora")
            else:
                error_body = response.text
                print(f"[Gemini API Error] Status: {response.status_code}, Body: {error_body}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro na API de IA (Status {response.status_code}): {error_body}"
                )
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar o comprovante: {str(e)}"
        )

    # 3. Salva o arquivo no servidor/MinIO usando a lógica existente em uploads.py
    import sys
    uploads_mod = sys.modules.get("app.routers.uploads")
    if not uploads_mod:
        import app.routers.uploads as uploads_mod
    url_comprovante = await uploads_mod._salvar_arquivo(arquivo, "comprovante")

    # 4. Atualiza os faturamentos da jornada ativa
    faturamento_existente = doc.get("faturamento") or {}
    if not isinstance(faturamento_existente, dict):
        faturamento_existente = {}

    val_uber = faturamento_existente.get("uber") or 0.0
    val_99 = faturamento_existente.get("noventa_nove") or 0.0
    val_outros = faturamento_existente.get("outros") or 0.0
    
    comp_uber = faturamento_existente.get("comprovante_uber_url")
    comp_99 = faturamento_existente.get("comprovante_99_url")
    comp_outros = faturamento_existente.get("comprovante_outros_url")

    if plataforma_final == "UBER":
        val_uber = round(val_uber + valor, 2)
        comp_uber = url_comprovante
    elif plataforma_final == "99":
        val_99 = round(val_99 + valor, 2)
        comp_99 = url_comprovante
    else:
        val_outros = round(val_outros + valor, 2)
        comp_outros = url_comprovante

    total_dia = round(val_uber + val_99 + val_outros, 2)

    novo_comprovante = {
        "plataforma": plataforma_final,
        "valor": valor,
        "origem": origem,
        "destino": destino,
        "data_hora": data_hora,
        "url_comprovante": url_comprovante,
        "data_processamento": datetime.now(timezone.utc).isoformat()
    }

    comprovantes_processados = faturamento_existente.get("comprovantes_processados") or []
    if not isinstance(comprovantes_processados, list):
        comprovantes_processados = []
    comprovantes_processados.append(novo_comprovante)

    faturamento_atualizado = {
        "uber": val_uber,
        "noventa_nove": val_99,
        "outros": val_outros,
        "total_dia": total_dia,
        "comprovante_uber_url": comp_uber,
        "comprovante_99_url": comp_99,
        "comprovante_outros_url": comp_outros,
        "comprovantes_processados": comprovantes_processados,
        "corridas_uber": faturamento_existente.get("corridas_uber") or 0,
        "corridas_99": faturamento_existente.get("corridas_99") or 0,
        "corridas_outros": faturamento_existente.get("corridas_outros") or 0
    }

    await db["jornadas"].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"faturamento": faturamento_atualizado}
        }
    )
    
    # Retorna o status e os valores extraídos
    return {
        "status": "sucesso",
        "plataforma": plataforma_final,
        "valor_extraido": valor,
        "origem": origem,
        "destino": destino,
        "data_hora": data_hora,
        "novo_total_plataforma": val_uber if plataforma_final == "UBER" else (val_99 if plataforma_final == "99" else val_outros),
        "url_comprovante": url_comprovante
    }


@router.post("/aberta/comprovante/revisao", status_code=201)
async def revisar_comprovante(
    url_comprovante: str = Form(...),
    plataforma: str = Form(...),
    valor: float = Form(...),
    origem: Optional[str] = Form(None),
    destino: Optional[str] = Form(None),
    data_hora: Optional[str] = Form(None),
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Recebe correções manuais de um comprovante que não teve todos os dados extraídos automaticamente.
    """
    # Encontra a jornada ativa
    doc = await db["jornadas"].find_one({
        "motorista_id": ObjectId(str(current_user.id)),
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]}
    })
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma jornada ativa encontrada para este motorista."
        )

    # Atualiza faturamento
    faturamento_existente = doc.get("faturamento") or {}
    if not isinstance(faturamento_existente, dict):
        faturamento_existente = {}

    val_uber = faturamento_existente.get("uber") or 0.0
    val_99 = faturamento_existente.get("noventa_nove") or 0.0
    val_outros = faturamento_existente.get("outros") or 0.0
    
    comp_uber = faturamento_existente.get("comprovante_uber_url")
    comp_99 = faturamento_existente.get("comprovante_99_url")
    comp_outros = faturamento_existente.get("comprovante_outros_url")

    if plataforma == "UBER":
        val_uber = round(val_uber + valor, 2)
        comp_uber = url_comprovante
    elif plataforma == "99":
        val_99 = round(val_99 + valor, 2)
        comp_99 = url_comprovante
    else:
        val_outros = round(val_outros + valor, 2)
        comp_outros = url_comprovante

    total_dia = round(val_uber + val_99 + val_outros, 2)

    novo_comprovante = {
        "plataforma": plataforma,
        "valor": valor,
        "origem": origem,
        "destino": destino,
        "data_hora": data_hora,
        "url_comprovante": url_comprovante,
        "data_processamento": datetime.now(timezone.utc).isoformat()
    }

    comprovantes_processados = faturamento_existente.get("comprovantes_processados") or []
    if not isinstance(comprovantes_processados, list):
        comprovantes_processados = []
        
    comprovantes_processados.append(novo_comprovante)

    faturamento_atualizado = {
        "uber": val_uber,
        "noventa_nove": val_99,
        "outros": val_outros,
        "total_dia": total_dia,
        "comprovante_uber_url": comp_uber,
        "comprovante_99_url": comp_99,
        "comprovante_outros_url": comp_outros,
        "comprovantes_processados": comprovantes_processados,
        "corridas_uber": faturamento_existente.get("corridas_uber") or 0,
        "corridas_99": faturamento_existente.get("corridas_99") or 0,
        "corridas_outros": faturamento_existente.get("corridas_outros") or 0
    }

    await db["jornadas"].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"faturamento": faturamento_atualizado}
        }
    )

    return {"status": "sucesso", "faturamento": faturamento_atualizado}


@router.post("/aberta/comprovante/deletar", status_code=200)
async def deletar_comprovante(
    url_comprovante: str = Form(...),
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Remove um comprovante específico da jornada aberta e ajusta o faturamento.
    """
    doc = await db["jornadas"].find_one({
        "motorista_id": ObjectId(str(current_user.id)),
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA"]}
    })
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma jornada ativa encontrada para este motorista."
        )

    faturamento = doc.get("faturamento") or {}
    comprovantes = faturamento.get("comprovantes_processados") or []
    
    # Encontra o comprovante a ser removido
    comprovante_alvo = None
    novos_comprovantes = []
    for c in comprovantes:
        if c.get("url_comprovante") == url_comprovante:
            comprovante_alvo = c
        else:
            novos_comprovantes.append(c)

    if not comprovante_alvo:
        raise HTTPException(
            status_code=404,
            detail="Comprovante não encontrado na jornada ativa."
        )

    # Subtrai o valor
    valor_subtrair = comprovante_alvo.get("valor", 0.0)
    plataforma = comprovante_alvo.get("plataforma", "OUTROS")

    val_uber = faturamento.get("uber") or 0.0
    val_99 = faturamento.get("noventa_nove") or 0.0
    val_outros = faturamento.get("outros") or 0.0

    if plataforma == "UBER":
        val_uber = max(0.0, round(val_uber - valor_subtrair, 2))
    elif plataforma == "99":
        val_99 = max(0.0, round(val_99 - valor_subtrair, 2))
    else:
        val_outros = max(0.0, round(val_outros - valor_subtrair, 2))

    total_dia = round(val_uber + val_99 + val_outros, 2)

    # Atualiza as URLs dos comprovantes principais
    comp_uber = faturamento.get("comprovante_uber_url")
    comp_99 = faturamento.get("comprovante_99_url")
    comp_outros = faturamento.get("comprovante_outros_url")

    def obter_ultimo_comprovante_url(plat):
        for c in reversed(novos_comprovantes):
            if c.get("plataforma") == plat:
                return c.get("url_comprovante")
        return None

    if comp_uber == url_comprovante:
        comp_uber = obter_ultimo_comprovante_url("UBER")
    if comp_99 == url_comprovante:
        comp_99 = obter_ultimo_comprovante_url("99")
    if comp_outros == url_comprovante:
        comp_outros = obter_ultimo_comprovante_url("OUTROS")

    faturamento_atualizado = {
        "uber": val_uber,
        "noventa_nove": val_99,
        "outros": val_outros,
        "total_dia": total_dia,
        "comprovante_uber_url": comp_uber,
        "comprovante_99_url": comp_99,
        "comprovante_outros_url": comp_outros,
        "comprovantes_processados": novos_comprovantes,
        "corridas_uber": faturamento.get("corridas_uber") or 0,
        "corridas_99": faturamento.get("corridas_99") or 0,
        "corridas_outros": faturamento.get("corridas_outros") or 0
    }

    await db["jornadas"].update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"faturamento": faturamento_atualizado}
        }
    )

    try:
        import sys
        uploads_mod = sys.modules.get("app.routers.uploads")
        if not uploads_mod:
            import app.routers.uploads as uploads_mod
        if "/uploads/comprovante/" in url_comprovante:
            filename = url_comprovante.split("/uploads/comprovante/")[-1]
            await uploads_mod.deletar_arquivo("comprovante", filename)
    except Exception as e:
        print(f"[DeletarComprovante] Erro ao deletar arquivo fisico: {e}")

    return {"status": "sucesso", "faturamento": faturamento_atualizado}


# ─── Validação de Fechamento & Corrida Particular ───────────────────────────

@router.post("/{jornada_id}/validar-fechamento")
async def validar_fechamento_jornada(
    jornada_id: str,
    faturamento_uber: float = 0.0,
    corridas_uber: int = 0,
    faturamento_99: float = 0.0,
    corridas_99: int = 0,
    faturamento_outros: float = 0.0,
    corridas_outros: int = 0,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    
    # Pegar comprovantes processados
    faturamento = doc.get("faturamento") or {}
    comprovantes = faturamento.get("comprovantes_processados") or []
    
    # Contar por plataforma
    detectados_uber = sum(1 for c in comprovantes if c.get("plataforma") == "UBER")
    detectados_99 = sum(1 for c in comprovantes if c.get("plataforma") == "99")
    detectados_outros = sum(1 for c in comprovantes if c.get("plataforma") == "OUTROS")
    
    status_uber = "OK" if detectados_uber == corridas_uber else "DIVERGENTE"
    status_99 = "OK" if detectados_99 == corridas_99 else "DIVERGENTE"
    status_outros = "OK" if detectados_outros == corridas_outros else "DIVERGENTE"
    
    pode_fechar = (status_uber == "OK") and (status_99 == "OK") and (status_outros == "OK")
    
    return {
        "comprovantes_processados": comprovantes,
        "comparativo": {
            "uber": {
                "declarado": corridas_uber,
                "detectado": detectados_uber,
                "status": status_uber,
                "diferenca": detectados_uber - corridas_uber
            },
            "noventa_nove": {
                "declarado": corridas_99,
                "detectado": detectados_99,
                "status": status_99,
                "diferenca": detectados_99 - corridas_99
            },
            "outros": {
                "declarado": corridas_outros,
                "detectado": detectados_outros,
                "status": status_outros,
                "diferenca": detectados_outros - corridas_outros
            }
        },
        "pode_fechar": pode_fechar
    }


@router.post("/{jornada_id}/corridas-particulares/iniciar")
async def iniciar_corrida_particular(
    jornada_id: str,
    km_inicio: float,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    destino_endereco: Optional[str] = None,
    destino_lat: Optional[float] = None,
    destino_lon: Optional[float] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    
    # Verifica se já existe corrida em andamento
    corridas = doc.get("corridas_particulares", [])
    if any(c.get("status") == "EM_ANDAMENTO" for c in corridas):
        raise HTTPException(status_code=400, detail="Já existe uma corrida particular em andamento.")
        
    # Calcula rota usando Google Directions API
    google_distancia_km = 0.0
    google_duracao_minutos = 0.0
    if settings.GOOGLE_API_KEY and localizacao_lat is not None and localizacao_lon is not None and destino_lat is not None and destino_lon is not None:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/directions/json",
                    params={
                        "origin": f"{localizacao_lat},{localizacao_lon}",
                        "destination": f"{destino_lat},{destino_lon}",
                        "key": settings.GOOGLE_API_KEY
                    },
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "OK" and data.get("routes"):
                        route = data["routes"][0]
                        leg = route["legs"][0]
                        google_distancia_km = leg["distance"]["value"] / 1000.0
                        google_duracao_minutos = leg["duration"]["value"] / 60.0
        except Exception as e:
            print("Erro ao calcular rota via Google Directions API:", e)

    # Fallback para OSRM se Google Maps falhou ou nao esta configurado
    if google_distancia_km == 0.0 and localizacao_lat is not None and localizacao_lon is not None and destino_lat is not None and destino_lon is not None:
        try:
            import httpx
            url = f"{settings.OSRM_URL}/route/v1/driving/{localizacao_lon},{localizacao_lat};{destino_lon},{destino_lat}?overview=false"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        google_distancia_km = route.get("distance", 0.0) / 1000.0
                        google_duracao_minutos = route.get("duration", 0.0) / 60.0
        except Exception as e:
            print("Erro no fallback OSRM para iniciar corrida:", e)

    nova_corrida = {
        "id": uuid.uuid4().hex[:8],
        "horario_inicio": datetime.now(timezone.utc).isoformat(),
        "horario_fim": None,
        "localizacao_inicio": {"lat": localizacao_lat, "lon": localizacao_lon} if localizacao_lat is not None else None,
        "localizacao_fim": None,
        "km_inicio": km_inicio,
        "km_fim": None,
        "km_rodados": None,
        "duracao_segundos": None,
        "valor_calculado": 0.0,
        "destino_endereco": destino_endereco,
        "destino_coordenadas": {"lat": destino_lat, "lon": destino_lon} if destino_lat is not None else None,
        "google_distancia_km": google_distancia_km,
        "google_duracao_minutos": google_duracao_minutos,
        "status": "EM_ANDAMENTO"
    }
    
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"corridas_particulares": nova_corrida}}
    )
    
    # Grava na coleção autônoma de corridas_particulares (Entidade própria)
    motorista_nome = current_user.nome if (current_user and hasattr(current_user, "nome")) else "Desconhecido"
    corrida_particular_doc = {
        "_id": nova_corrida["id"],
        "id_corrida": nova_corrida["id"],
        "jornada_id": jornada_id,
        "motorista_id": str(doc.get("motorista_id")) if doc.get("motorista_id") else None,
        "motorista_nome": motorista_nome,
        "veiculo_id": doc.get("veiculo_id"),
        "horario_inicio": nova_corrida["horario_inicio"],
        "horario_fim": None,
        "localizacao_inicio": nova_corrida["localizacao_inicio"],
        "localizacao_fim": None,
        "km_inicio": nova_corrida["km_inicio"],
        "km_fim": None,
        "km_rodados": None,
        "duracao_segundos": None,
        "valor_calculado": 0.0,
        "destino_endereco": destino_endereco,
        "destino_coordenadas": nova_corrida["destino_coordenadas"],
        "google_distancia_km": google_distancia_km,
        "google_duracao_minutos": google_duracao_minutos,
        "status": "EM_ANDAMENTO"
    }
    await db["corridas_particulares"].insert_one(corrida_particular_doc)
    
    return nova_corrida


@router.post("/{jornada_id}/corridas-particulares/{corrida_id}/finalizar")
async def finalizar_corrida_particular(
    jornada_id: str,
    corrida_id: str,
    km_fim: Optional[float] = None,
    justificativa: Optional[str] = None,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
        
    corridas = doc.get("corridas_particulares", [])
    corrida = next((c for c in corridas if c["id"] == corrida_id), None)
    if not corrida:
        raise HTTPException(status_code=404, detail="Corrida particular não encontrada")
        
    if corrida.get("status") == "FINALIZADA":
        return corrida
        
    horario_fim = datetime.now(timezone.utc)
    horario_inicio = datetime.fromisoformat(corrida["horario_inicio"])
    duracao_segundos = int((horario_fim - horario_inicio).total_seconds())
    duracao_minutos = duracao_segundos / 60.0
    
    km_inicio = corrida["km_inicio"]
    if km_fim is None or km_fim == 0.0:
        km_rodados = corrida.get("google_distancia_km") or 0.0
        km_fim = round(km_inicio + km_rodados, 1)
    else:
        km_rodados = round(km_fim - km_inicio, 1)
        if km_rodados < 0:
            km_rodados = 0.0

    # Buscar faixas de preços configuradas no banco
    faixas = await db["precos_particulares"].find().to_list(None)
    
    # Lógica de correspondência de horário
    # Usar hora local (America/Sao_Paulo) para as faixas horárias
    tz = zoneinfo.ZoneInfo("America/Sao_Paulo")
    hora_local_inicio = horario_inicio.astimezone(tz).time()
    hora_local_fim = horario_fim.astimezone(tz).time()
    
    def obter_preco_para_horario(horario: time):
        for f in faixas:
            try:
                h_ini = time.fromisoformat(f["hora_inicio"])
                h_fim = time.fromisoformat(f["hora_fim"])
            except Exception:
                continue
            if h_ini <= h_fim:
                if h_ini <= horario <= h_fim:
                    return f["preco_km"], f["preco_minuto"]
            else:
                if horario >= h_ini or horario <= h_fim:
                    return f["preco_km"], f["preco_minuto"]
        # Fallbacks globais se nenhuma faixa cadastrada
        return 2.0, 0.5
        
    preco_km, _ = obter_preco_para_horario(hora_local_inicio)
    _, preco_minuto = obter_preco_para_horario(hora_local_fim)
    
    valor_calculado = round((km_rodados * preco_km) + (duracao_minutos * preco_minuto), 2)
    
    # Atualizar a corrida na jornada
    await db["jornadas"].update_one(
        {"_id": jornada_id, "corridas_particulares.id": corrida_id},
        {
            "$set": {
                "corridas_particulares.$.horario_fim": horario_fim.isoformat(),
                "corridas_particulares.$.localizacao_fim": {"lat": localizacao_lat, "lon": localizacao_lon} if localizacao_lat is not None else None,
                "corridas_particulares.$.km_fim": km_fim,
                "corridas_particulares.$.km_rodados": km_rodados,
                "corridas_particulares.$.duracao_segundos": duracao_segundos,
                "corridas_particulares.$.valor_calculado": valor_calculado,
                "corridas_particulares.$.justificativa": justificativa,
                "corridas_particulares.$.status": "FINALIZADA"
            }
        }
    )
    
    # Atualizar faturamento acumulado na jornada
    faturamento = doc.get("faturamento") or {}
    val_uber = faturamento.get("uber") or 0.0
    val_99 = faturamento.get("noventa_nove") or 0.0
    val_outros = faturamento.get("outros") or 0.0
    
    val_outros_novo = round(val_outros + valor_calculado, 2)
    total_dia_novo = round(val_uber + val_99 + val_outros_novo, 2)
    
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {
            "$set": {
                "faturamento.outros": val_outros_novo,
                "faturamento.total_dia": total_dia_novo
            }
        }
    )
    
    # Retorna objeto atualizado
    corrida_atualizada = {
        **corrida,
        "horario_fim": horario_fim.isoformat(),
        "localizacao_fim": {"lat": localizacao_lat, "lon": localizacao_lon} if localizacao_lat is not None else None,
        "km_fim": km_fim,
        "km_rodados": km_rodados,
        "duracao_segundos": duracao_segundos,
        "valor_calculado": valor_calculado,
        "justificativa": justificativa,
        "status": "FINALIZADA"
    }

    # Atualizar na coleção autônoma de corridas_particulares
    await db["corridas_particulares"].update_one(
        {"id_corrida": corrida_id},
        {
            "$set": {
                "horario_fim": corrida_atualizada["horario_fim"],
                "localizacao_fim": corrida_atualizada["localizacao_fim"],
                "km_fim": corrida_atualizada["km_fim"],
                "km_rodados": corrida_atualizada["km_rodados"],
                "duracao_segundos": corrida_atualizada["duracao_segundos"],
                "valor_calculado": corrida_atualizada["valor_calculado"],
                "justificativa": justificativa,
                "status": "FINALIZADA"
            }
        },
        upsert=True
    )
    
    return corrida_atualizada


@router.delete("/{jornada_id}")
async def deletar_jornada(
    jornada_id: str,
    db=Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.GESTOR))
):
    """
    Remove uma jornada do banco de dados (endpoint administrativo temporário).
    """
    try:
        from bson import ObjectId
        query = {"$or": [{"_id": jornada_id}]}
        if ObjectId.is_valid(jornada_id):
            query["$or"].append({"_id": ObjectId(jornada_id)})

        res = await db["jornadas"].delete_one(query)
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Jornada não encontrada")

        # Também remove os registros de GPS associados
        gps_query = {"$or": [{"jornada_id": jornada_id}]}
        if ObjectId.is_valid(jornada_id):
            gps_query["$or"].append({"jornada_id": ObjectId(jornada_id)})

        try:
            await db["historico_gps"].delete_many(gps_query)
        except Exception:
            pass

        return {"status": "ok", "message": "Jornada deletada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao deletar jornada: {str(e)}")


def _deletar_arquivo_por_url(url: str):
    if not url:
        return
    parts = url.split("/static/uploads/")
    if len(parts) < 2:
        url_parts = [p for p in url.split("/") if p]
        if len(url_parts) >= 2:
            contexto = url_parts[-2]
            filename = url_parts[-1]
        else:
            return
    else:
        path_parts = parts[1].split("/")
        if len(path_parts) >= 2:
            contexto = path_parts[0]
            filename = path_parts[1]
        else:
            return

    try:
        from app.routers.uploads import UPLOAD_DIR, MINIO_ENABLED, MINIO_CLIENT, MINIO_BUCKET
        if MINIO_ENABLED and MINIO_CLIENT:
            try:
                object_name = f"{contexto}/{filename}"
                MINIO_CLIENT.remove_object(MINIO_BUCKET, object_name)
            except Exception:
                pass
        filepath = UPLOAD_DIR / contexto / filename
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass
    except Exception as e:
        print(f"Erro ao deletar arquivo por URL {url}: {e}")


@router.get("/{jornada_id}/auditoria")
async def obter_auditoria_sessao(
    jornada_id: str,
    db=Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.GESTOR))
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
        
    return {
        "jornada_id": jornada_id,
        "motorista_nome": doc.get("motorista_nome"),
        "veiculo_id": doc.get("veiculo_id"),
        "auditoria_status": doc.get("auditoria_status", "PENDENTE"),
        "fotos": {
            "km_inicial_url": doc.get("fotos", {}).get("km_inicial_url"),
            "km_final_url": doc.get("fotos", {}).get("km_final_url"),
            "foto_avarias_url": doc.get("vistoria", {}).get("foto_avarias_url")
        },
        "comprovantes": [
            {
                "plataforma": c.get("plataforma"),
                "valor": c.get("valor"),
                "url_comprovante": c.get("url_comprovante")
            } for c in (doc.get("faturamento", {}).get("comprovantes_processados") or [])
        ]
    }


@router.post("/{jornada_id}/auditoria/aprovar")
async def aprovar_auditoria_sessao(
    jornada_id: str,
    db=Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.GESTOR))
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    urls_to_delete = []
    
    km_ini = doc.get("fotos", {}).get("km_inicial_url")
    if km_ini:
        urls_to_delete.append(km_ini)
    km_fim = doc.get("fotos", {}).get("km_final_url")
    if km_fim:
        urls_to_delete.append(km_fim)
        
    avarias = doc.get("vistoria", {}).get("foto_avarias_url")
    if avarias:
        urls_to_delete.append(avarias)
        
    for c in (doc.get("faturamento", {}).get("comprovantes_processados") or []):
        url_c = c.get("url_comprovante")
        if url_c:
            urls_to_delete.append(url_c)

    for url in urls_to_delete:
        _deletar_arquivo_por_url(url)

    update_data = {
        "auditoria_status": "APROVADA",
        "fotos.km_inicial_url": None,
        "fotos.km_final_url": None,
        "vistoria.foto_avarias_url": None,
    }

    if "faturamento" in doc:
        update_data["faturamento.comprovantes_processados"] = []
        update_data["faturamento.comprovante_uber_url"] = None
        update_data["faturamento.comprovante_99_url"] = None
        update_data["faturamento.comprovante_outros_url"] = None

    await db["jornadas"].update_one({"_id": jornada_id}, {"$set": update_data})
    
    return {"status": "ok", "message": "Auditoria aprovada e mídias removidas com sucesso"}


@router.post("/admin/limpar-dados-antigos")
async def limpar_dados_antigos(
    dias: int = 30,
    limpar_raw_gps: bool = True,
    limpar_arquivos_zip: bool = False,
    limpar_jornadas_completas: bool = False,
    db=Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN)),
):
    """
    Rotina administrativa para eliminar dados antigos do sistema.
    """
    from datetime import datetime, timedelta, timezone
    
    limite_data = datetime.now(timezone.utc) - timedelta(days=dias)
    relatorio = {
        "status": "sucesso",
        "dias_limite": dias,
        "data_limite": limite_data.isoformat(),
        "itens_deletados": {}
    }
    
    # 1. Limpar raw gps points
    if limpar_raw_gps:
        res = await db["historico_gps"].delete_many({"timestamp": {"$lt": limite_data}})
        relatorio["itens_deletados"]["raw_gps"] = res.deleted_count

    # 2. Limpar arquivos zip e referências
    if limpar_arquivos_zip:
        data_str_limite = limite_data.date().isoformat()
        
        jornadas_antigas = await db["jornadas"].find({
            "status": "ENCERRADA",
            "horario.data": {"$lt": data_str_limite},
            "telemetria_url": {"$ne": None}
        }).to_list(10000)
        
        from app.routers.uploads import MINIO_CLIENT, MINIO_BUCKET, MINIO_ENABLED, UPLOAD_DIR
        
        arquivos_removidos = 0
        for j in jornadas_antigas:
            url = j.get("telemetria_url")
            if not url:
                continue
            
            # Deletar arquivo físico
            if MINIO_ENABLED and MINIO_CLIENT:
                if url.startswith(f"/{MINIO_BUCKET}/"):
                    obj_path = url[len(f"/{MINIO_BUCKET}/"):]
                    try:
                        MINIO_CLIENT.remove_object(MINIO_BUCKET, obj_path)
                        arquivos_removidos += 1
                    except Exception as e:
                        print("Erro ao remover objeto MinIO:", e)
            else:
                if url.startswith("/static/uploads/"):
                    rel_path = url[len("/static/uploads/"):]
                    local_path = UPLOAD_DIR / rel_path
                    if local_path.exists():
                        try:
                            local_path.unlink()
                            arquivos_removidos += 1
                        except Exception as e:
                            print("Erro ao remover arquivo local:", e)
                            
            # Atualizar jornada para remover a referência
            await db["jornadas"].update_one(
                {"_id": j["_id"]},
                {"$set": {"telemetria_url": None, "rota_polyline": None}}
            )
            
        relatorio["itens_deletados"]["arquivos_telemetria"] = arquivos_removidos

    # 3. Limpar jornadas completas
    if limpar_jornadas_completas:
        data_str_limite = limite_data.date().isoformat()
        res = await db["jornadas"].delete_many({
            "status": "ENCERRADA",
            "horario.data": {"$lt": data_str_limite}
        })
        relatorio["itens_deletados"]["jornadas"] = res.deleted_count
        
    return relatorio
