from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.db.database import get_db
from app.models.user import UserPublic
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/metricas", tags=["Métricas e KPIs"])


def _calcular_metricas_jornada_doc(jornada: dict) -> dict:
    fat = jornada.get("faturamento", {})
    total_faturamento = float(fat.get("total_dia") or 0.0)
    if total_faturamento == 0.0:
        total_faturamento = (
            float(fat.get("uber") or 0.0) +
            float(fat.get("noventa_nove") or 0.0) +
            float(fat.get("outros") or 0.0)
        )

    km_data = jornada.get("km", {})
    km_rodados = float(km_data.get("rodados") or 0.0)
    if km_rodados == 0.0 and km_data.get("final") and km_data.get("inicial"):
        km_rodados = max(0.0, float(km_data["final"]) - float(km_data["inicial"]))

    # Calcular KM produtivo
    segmentos = jornada.get("segmentos_rota", [])
    km_produtivo = 0.0
    for seg in segmentos:
        if seg.get("is_produtivo") or seg.get("status") == "produtivo":
            km_produtivo += float(seg.get("km") or 0.0)

    # Qtd de corridas
    corridas_uber = int(fat.get("corridas_uber") or 0)
    corridas_99 = int(fat.get("corridas_99") or 0)
    corridas_outros = int(fat.get("corridas_outros") or 0)
    corridas_particulares = len(jornada.get("corridas_particulares", []))
    total_corridas = corridas_uber + corridas_99 + corridas_outros + corridas_particulares

    # Evitar divisão por zero
    fat_km_global = round(total_faturamento / km_rodados, 2) if km_rodados > 0 else 0.0
    fat_km_util = round(total_faturamento / km_produtivo, 2) if km_produtivo > 0 else 0.0
    ticket_medio = round(total_faturamento / total_corridas, 2) if total_corridas > 0 else 0.0

    return {
        "jornada_id": str(jornada.get("_id")),
        "data": jornada.get("data"),
        "total_faturamento": round(total_faturamento, 2),
        "km_rodados_global": round(km_rodados, 2),
        "km_rodados_util": round(km_produtivo, 2),
        "total_corridas": total_corridas,
        "faturamento_km_global": fat_km_global,
        "faturamento_km_util": fat_km_util,
        "ticket_medio": ticket_medio,
    }


@router.get("/jornada/{jornada_id}")
async def obter_metricas_jornada(
    jornada_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    try:
        q_j = {"$or": [{"_id": jornada_id}, {"_id": ObjectId(jornada_id)}]}
    except Exception:
        q_j = {"_id": jornada_id}

    jornada = await db["jornadas"].find_one(q_j)
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    return _calcular_metricas_jornada_doc(jornada)


@router.get("/motorista/{motorista_id}/acumulado")
async def obter_acumulado_motorista(
    motorista_id: str,
    mes: Optional[str] = None,  # YYYY-MM
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if not mes:
        now = datetime.now(timezone.utc)
        mes = f"{now.year}-{now.month:02d}"

    query = {
        "$or": [{"motorista_id": motorista_id}],
        "data": {"$regex": f"^{mes}"}
    }
    if ObjectId.is_valid(motorista_id):
        query["$or"].append({"motorista_id": ObjectId(motorista_id)})

    jornadas = await db["jornadas"].find(query).to_list(500)

    total_fat = 0.0
    total_km_global = 0.0
    total_km_util = 0.0
    total_corridas = 0
    total_horas_segundos = 0

    for j in jornadas:
        m = _calcular_metricas_jornada_doc(j)
        total_fat += m["total_faturamento"]
        total_km_global += m["km_rodados_global"]
        total_km_util += m["km_rodados_util"]
        total_corridas += m["total_corridas"]
        
        horario = j.get("horario", {})
        total_horas_segundos += int(horario.get("total_horas_segundos") or 0)

    total_dias = len(jornadas)
    fat_km_global_mes = round(total_fat / total_km_global, 2) if total_km_global > 0 else 0.0
    fat_km_util_mes = round(total_fat / total_km_util, 2) if total_km_util > 0 else 0.0
    ticket_medio_mes = round(total_fat / total_corridas, 2) if total_corridas > 0 else 0.0
    media_diaria_fat = round(total_fat / total_dias, 2) if total_dias > 0 else 0.0
    horas_trabalhadas = round(total_horas_segundos / 3600.0, 1)

    return {
        "mes": mes,
        "total_jornadas": total_dias,
        "total_faturamento": round(total_fat, 2),
        "media_diaria_faturamento": media_diaria_fat,
        "total_km_global": round(total_km_global, 2),
        "total_km_util": round(total_km_util, 2),
        "total_corridas": total_corridas,
        "total_horas_trabalhadas": horas_trabalhadas,
        "faturamento_km_global": fat_km_global_mes,
        "faturamento_km_util": fat_km_util_mes,
        "ticket_medio": ticket_medio_mes,
    }


@router.get("/motorista/{motorista_id}/progresso-metas")
async def obter_progresso_metas(
    motorista_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    acumulado = await obter_acumulado_motorista(motorista_id, None, db, current_user)
    
    # Buscar jornada de hoje se houver
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    q_today = {
        "$or": [{"motorista_id": motorista_id}],
        "data": today_str
    }
    if ObjectId.is_valid(motorista_id):
        q_today["$or"].append({"motorista_id": ObjectId(motorista_id)})

    jornada_hoje = await db["jornadas"].find_one(q_today)
    metricas_hoje = _calcular_metricas_jornada_doc(jornada_hoje) if jornada_hoje else {
        "total_faturamento": 0.0,
        "faturamento_km_global": 0.0,
        "faturamento_km_util": 0.0,
        "ticket_medio": 0.0
    }
    horas_hoje = round(int((jornada_hoje or {}).get("horario", {}).get("total_horas_segundos") or 0) / 3600.0, 1)

    metas_docs = await db["metas_bonus"].find().to_list(100)

    lista_progresso = []
    for meta in metas_docs:
        meta_id = str(meta.get("_id"))
        tipo = meta.get("tipo", "").upper()
        descricao = meta.get("descricao") or f"Meta: {tipo}"
        
        # Define valor alvo da meta
        target = float(meta.get("meta_alvo") or meta.get("faixa_minima") or 0.0)
        actual = 0.0

        if tipo in ["FATURAMENTO_KM", "FATURAMENTO_POR_KM"]:
            actual = metricas_hoje["faturamento_km_global"]
            descricao = "Faturamento / KM Global"
        elif tipo in ["TICKET_MEDIO"]:
            actual = metricas_hoje["ticket_medio"]
            descricao = "Ticket Médio por Corrida"
        elif tipo in ["HORAS_DIA", "HORAS_DIARIAS"]:
            actual = horas_hoje
            target = target or 8.8
            descricao = "Meta de Horas Diárias"
        elif tipo in ["HORAS_MES", "HORAS_MENSAIS"]:
            actual = acumulado["total_horas_trabalhadas"]
            target = target or 220.0
            descricao = "Meta de Horas Mensais"
        elif tipo in ["FATURAMENTO_DIA", "FATURAMENTO_DIARIO"]:
            actual = metricas_hoje["total_faturamento"]
            descricao = "Meta de Faturamento Diário"
        elif tipo in ["FATURAMENTO_MES", "FATURAMENTO_MENSAL"]:
            actual = acumulado["total_faturamento"]
            descricao = "Meta de Faturamento Mensal"
        else:
            actual = metricas_hoje["total_faturamento"]

        pct = round((actual / target * 100.0), 1) if target > 0 else 0.0
        pct = min(pct, 100.0)

        lista_progresso.append({
            "id": meta_id,
            "tipo": tipo,
            "descricao": descricao,
            "meta_alvo": target,
            "valor_atual": actual,
            "progresso_pct": pct,
            "atingida": actual >= target if target > 0 else False
        })

    return {
        "motorista_id": motorista_id,
        "metricas_hoje": metricas_hoje,
        "acumulado_mes": acumulado,
        "metas": lista_progresso
    }
