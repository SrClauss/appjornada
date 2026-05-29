from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.db.database import get_db
from app.models.historico_gps import GeoPoint, HistoricoGPS, HistoricoGPSCreate
from app.models.user import Role, UserPublic
from app.core.dependencies import get_current_user, require_roles

# Limiar para considerar motorista parado (metros)
LIMIAR_PARADO_M = 50
# Tempo máximo parado sem justificativa para gerar alerta (minutos)
MINUTOS_INATIVIDADE_ALERTA = 15

router = APIRouter(prefix="/gps", tags=["gps"])


@router.post("", response_model=HistoricoGPS, status_code=201)
async def registrar_ponto_gps(
    dados: HistoricoGPSCreate,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Recebido pelo app mobile a cada 15 segundos durante a jornada."""
    doc = dados.model_dump()
    doc["motorista_id"] = ObjectId(str(dados.motorista_id))
    doc["timestamp"] = dados.timestamp or datetime.now(timezone.utc)

    resultado = await db["historico_gps"].insert_one(doc)
    criado = await db["historico_gps"].find_one({"_id": resultado.inserted_id})
    return HistoricoGPS(**criado)


@router.get("/motorista/{motorista_id}", response_model=List[HistoricoGPS])
async def historico_motorista(
    motorista_id: str,
    jornada_id: Optional[str] = None,
    limite: int = 500,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    filtro: dict = {"motorista_id": ObjectId(motorista_id)}
    if jornada_id:
        filtro["jornada_id"] = jornada_id

    docs = await db["historico_gps"].find(filtro).sort("timestamp", -1).to_list(limite)
    return [HistoricoGPS(**d) for d in docs]


@router.get("/alertas-inatividade", tags=["alertas"])
async def alertas_inatividade(
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    """
    Detecta motoristas com jornada aberta que estão parados
    por mais de MINUTOS_INATIVIDADE_ALERTA sem pausa registrada.
    """
    from datetime import timedelta

    alertas = []
    jornadas_abertas = await db["jornadas"].find(
        {"status": {"$in": ["ABERTA", "EM_ANDAMENTO"]}}
    ).to_list(100)

    for jornada in jornadas_abertas:
        motorista_id = jornada["motorista_id"]
        limite_tempo = datetime.now(timezone.utc) - timedelta(minutes=MINUTOS_INATIVIDADE_ALERTA)

        # Últimos pontos GPS no período
        pontos = await db["historico_gps"].find({
            "motorista_id": motorista_id,
            "jornada_id": jornada["_id"],
            "timestamp": {"$gte": limite_tempo},
        }).sort("timestamp", 1).to_list(200)

        if not pontos:
            continue

        # Verifica se todos os pontos estão dentro do limiar (parado)
        todos_parados = all(
            (p.get("distancia_ultima_m") or 0) <= LIMIAR_PARADO_M
            for p in pontos
        )

        # Verifica se há pausa aberta que justifique
        tem_pausa_aberta = any(
            p.get("fim") is None for p in jornada.get("pausas", [])
        )

        if todos_parados and not tem_pausa_aberta:
            alertas.append({
                "jornada_id": jornada["_id"],
                "motorista_id": str(motorista_id),
                "tipo": "INATIVIDADE_SEM_JUSTIFICATIVA",
                "minutos_parado": MINUTOS_INATIVIDADE_ALERTA,
                "ultimo_ponto": pontos[-1].get("timestamp"),
            })

    return {"total_alertas": len(alertas), "alertas": alertas}
