from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role
from app.models.veiculo import Veiculo, VeiculoCreate, VeiculoUpdate
from app.core.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/veiculos", tags=["veículos"])


@router.post("/", response_model=Veiculo, status_code=201)
async def criar_veiculo(
    dados: VeiculoCreate,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    doc = dados.model_dump()
    doc["_id"] = dados.id_placa
    try:
        await db["veiculos"].insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Veículo já cadastrado com esta placa",
        )
    return Veiculo(**doc)


@router.get("/", response_model=List[Veiculo])
async def listar_veiculos(
    db=Depends(get_db),
    _=Depends(get_current_user),
):
    docs = await db["veiculos"].find().to_list(200)
    return [Veiculo(**d) for d in docs]


@router.get("/{placa}", response_model=Veiculo)
async def get_veiculo(placa: str, db=Depends(get_db), _=Depends(get_current_user)):
    doc = await db["veiculos"].find_one({"_id": placa})
    if not doc:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return Veiculo(**doc)


@router.patch("/{placa}", response_model=Veiculo)
async def atualizar_veiculo(
    placa: str,
    dados: VeiculoUpdate,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    update = dados.model_dump(exclude_none=True)
    resultado = await db["veiculos"].update_one({"_id": placa}, {"$set": update})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    doc = await db["veiculos"].find_one({"_id": placa})
    return Veiculo(**doc)


@router.delete("/{placa}", status_code=204)
async def deletar_veiculo(
    placa: str,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN)),
):
    resultado = await db["veiculos"].delete_one({"_id": placa})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
