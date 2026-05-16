from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role, UserPublic, UserUpdate
from app.core.dependencies import get_current_user, require_roles
from app.core.security import hash_senha

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserPublic])
async def listar_users(
    role: Optional[Role] = None,
    situacao: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    filtro = {}
    if role:
        filtro["role"] = role
    if situacao:
        filtro["situacao"] = situacao
    limit = min(limit, 200)
    docs = await db["users"].find(filtro).skip(skip).to_list(limit)
    return [UserPublic(**d) for d in docs]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    # motorista só pode ver a si mesmo
    if current_user.role == Role.MOTORISTA and str(current_user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserPublic(**doc)


@router.patch("/{user_id}", response_model=UserPublic)
async def atualizar_user(
    user_id: str,
    dados: UserUpdate,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role == Role.MOTORISTA and str(current_user.id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    update = dados.model_dump(exclude_none=True)
    if "senha" in update:
        update["senha_hash"] = hash_senha(update.pop("senha"))
    if "pin" in update:
        update["pin_hash"] = hash_senha(update.pop("pin"))

    await db["users"].update_one({"_id": ObjectId(user_id)}, {"$set": update})
    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    return UserPublic(**doc)


@router.delete("/{user_id}", status_code=204)
async def deletar_user(
    user_id: str,
    db=Depends(get_db),
    _=Depends(require_roles(Role.ADMIN)),
):
    """Inativa o usuário (soft delete) — preserva histórico de jornadas."""
    resultado = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"situacao": "Inativo"}},
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
