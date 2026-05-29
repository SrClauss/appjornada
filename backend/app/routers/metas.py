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
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    """Retorna o bônus aplicável dado o faturamento do dia."""
    metas = await db["metas_bonus"].find().sort("faixa_minima", 1).to_list(50)
    bonus_aplicavel = None
    for meta in metas:
        fmin = meta.get("faixa_minima") or 0
        fmax = meta.get("faixa_maxima")
        if faturamento_dia >= fmin and (fmax is None or faturamento_dia <= fmax):
            bonus_aplicavel = meta
    return {
        "motorista_id": motorista_id,
        "faturamento_dia": faturamento_dia,
        "bonus": bonus_aplicavel.get("bonus") if bonus_aplicavel else 0,
        "meta_aplicada": bonus_aplicavel.get("tipo") if bonus_aplicavel else None,
    }
