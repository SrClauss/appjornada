from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from app.db.database import get_db
from app.models.manutencao import Manutencao, ManutencaoCreate, ManutencaoUpdate
from app.models.user import Role
from app.core.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/manutencoes", tags=["manutenções"])


@router.post("", response_model=Manutencao, status_code=201)
async def registrar_manutencao(
    dados: ManutencaoCreate,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    doc = dados.model_dump()
    if dados.motorista_id:
        doc["motorista_id"] = ObjectId(str(dados.motorista_id))
    resultado = await db["manutencoes"].insert_one(doc)
    criado = await db["manutencoes"].find_one({"_id": resultado.inserted_id})
    return Manutencao(**criado)


@router.get("", response_model=List[Manutencao])
async def listar_manutencoes(
    veiculo_id: Optional[str] = None,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    filtro: dict = {}
    if veiculo_id:
        filtro["veiculo_id"] = veiculo_id
    if current_user.role == Role.MOTORISTA:
        filtro["motorista_id"] = ObjectId(str(current_user.id))

    docs = await db["manutencoes"].find(filtro).sort("entrada", -1).to_list(200)
    return [Manutencao(**d) for d in docs]


@router.get("/{manutencao_id}", response_model=Manutencao)
async def get_manutencao(
    manutencao_id: str,
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    doc = await db["manutencoes"].find_one({"_id": ObjectId(manutencao_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Manutenção não encontrada")
    return Manutencao(**doc)


@router.patch("/{manutencao_id}", response_model=Manutencao)
async def atualizar_manutencao(
    manutencao_id: str,
    dados: ManutencaoUpdate,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    update = dados.model_dump(exclude_none=True)
    resultado = await db["manutencoes"].update_one(
        {"_id": ObjectId(manutencao_id)}, {"$set": update}
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Manutenção não encontrada")
    doc = await db["manutencoes"].find_one({"_id": ObjectId(manutencao_id)})
    return Manutencao(**doc)
