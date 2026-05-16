import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role, UserPublic
from app.models.jornada import (
    Jornada, JornadaCreate, JornadaUpdate,
    Pausa, Abastecimento, Sinistro,
)
from app.core.dependencies import get_current_user, require_roles
from app.core.security import verificar_senha

router = APIRouter(prefix="/jornadas", tags=["jornadas"])

HORAS_DIARIAS_CLT = 8.0
HORAS_SEMANAIS_CLT = 44.0
HORAS_MENSAIS_CLT = 220.0


def _calcular_saldo_horas(segundos: Optional[int]) -> Optional[float]:
    if segundos is None:
        return None
    trabalhadas = segundos / 3600
    return round(trabalhadas - HORAS_DIARIAS_CLT, 2)


# ─── CRUD principal ──────────────────────────────────────────────────────────

@router.post("/", response_model=Jornada, status_code=201)
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
        "data": hoje,
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO"]},
    })
    if aberta:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma jornada aberta para hoje",
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
    return Jornada(**criado)


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
    return Jornada(**doc) if doc else None


@router.get("/", response_model=List[Jornada])
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
    return [Jornada(**d) for d in docs]


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
    return Jornada(**doc)


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
    return Jornada(**atualizado)


# ─── Fechar jornada ──────────────────────────────────────────────────────────

@router.patch("/{jornada_id}/fechar", response_model=Jornada)
async def fechar_jornada(
    jornada_id: str,
    km_final: float,
    faturamento_uber: float = 0.0,
    faturamento_99: float = 0.0,
    faturamento_outros: float = 0.0,
    foto_km_final_url: Optional[str] = None,
    localizacao_lat: Optional[float] = None,
    localizacao_lon: Optional[float] = None,
    observacoes: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    doc = await db["jornadas"].find_one({"_id": jornada_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    if doc["status"] not in ("ABERTA", "EM_ANDAMENTO"):
        raise HTTPException(status_code=409, detail="Jornada já encerrada")

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
        "saldo_horas_dia": _calcular_saldo_horas(total_segundos),
    }
    # Registra localização final se fornecida
    if localizacao_lat is not None and localizacao_lon is not None:
        update["localizacao_final"] = {"lat": localizacao_lat, "lon": localizacao_lon}
    if foto_km_final_url:
        update["fotos.km_final_url"] = foto_km_final_url
    if observacoes:
        update["observacoes"] = observacoes

    await db["jornadas"].update_one({"_id": jornada_id}, {"$set": update})
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**atualizado)


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
    return Jornada(**atualizado)


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
    return Jornada(**atualizado)


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

    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"abastecimentos": dados.model_dump()}},
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**atualizado)


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

    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$push": {"sinistros": dados.model_dump()}},
    )
    atualizado = await db["jornadas"].find_one({"_id": jornada_id})
    return Jornada(**atualizado)


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
