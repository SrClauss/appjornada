from typing import List
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.db.database import get_db
from app.models.meta_bonus import MetaBonus, MetaBonusCreate, MetaBonusUpdate
from app.models.user import Role
from app.core.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/metas", tags=["metas e bônus"])


@router.post("", response_model=MetaBonus, status_code=201)
async def criar_meta(
    dados: MetaBonusCreate,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    doc = dados.model_dump()
    resultado = await db["metas_bonus"].insert_one(doc)
    criado = await db["metas_bonus"].find_one({"_id": resultado.inserted_id})
    return MetaBonus(**criado)


@router.get("", response_model=List[MetaBonus])
async def listar_metas(
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    docs = await db["metas_bonus"].find().to_list(100)
    return [MetaBonus(**d) for d in docs]


@router.patch("/{meta_id}", response_model=MetaBonus)
async def atualizar_meta(
    meta_id: str,
    dados: MetaBonusUpdate,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    update = dados.model_dump(exclude_none=True)
    resultado = await db["metas_bonus"].update_one(
        {"_id": ObjectId(meta_id)}, {"$set": update}
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    doc = await db["metas_bonus"].find_one({"_id": ObjectId(meta_id)})
    return MetaBonus(**doc)


@router.delete("/{meta_id}", status_code=204)
async def deletar_meta(
    meta_id: str,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN)),
):
    resultado = await db["metas_bonus"].delete_one({"_id": ObjectId(meta_id)})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meta não encontrada")


@router.get("/calcular-bonus/{motorista_id}", tags=["dashboard"])
async def calcular_bonus(
    motorista_id: str,
    faturamento_dia: float,
    hora_inicio: Optional[str] = None,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """Retorna o bônus aplicável dado o faturamento do dia e opcionalmente a hora de início da jornada."""
    from datetime import date, time as dt_time
    from typing import Optional as Opt
    
    j_time = None
    if hora_inicio:
        try:
            parts = hora_inicio.split(":")
            j_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        except Exception:
            pass
            
    if not j_time:
        hoje = date.today().isoformat()
        try:
            from bson import ObjectId
            query = {"data": hoje, "$or": [{"motorista_id": motorista_id}]}
            if ObjectId.is_valid(motorista_id):
                query["$or"].append({"motorista_id": ObjectId(motorista_id)})
            jornada = await db["jornadas"].find_one(query, sort=[("horario.inicio", -1)])
            if jornada:
                journey_inicio = jornada.get("horario", {}).get("inicio")
                if journey_inicio:
                    parts = journey_inicio.split(":")
                    j_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        except Exception:
            pass

    metas = await db["metas_bonus"].find().sort("faixa_minima", 1).to_list(50)
    bonus_aplicavel = None
    
    for meta in metas:
        fmin = meta.get("faixa_minima") or 0.0
        fmax = meta.get("faixa_maxima")
        if faturamento_dia >= fmin and (fmax is None or faturamento_dia <= fmax):
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
                except Exception:
                    continue
            
            bonus_aplicavel = meta

    return {
        "motorista_id": motorista_id,
        "faturamento_dia": faturamento_dia,
        "bonus": bonus_aplicavel.get("bonus") if bonus_aplicavel else 0,
        "meta_aplicada": bonus_aplicavel.get("tipo") if bonus_aplicavel else None,
    }
