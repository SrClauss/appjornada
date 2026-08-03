from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.db.database import get_db
from app.models.user import Role, UserPublic, UserUpdate
from app.core.dependencies import get_current_user, require_roles
from app.core.security import hash_senha
from app.db.audit import registrar_auditoria

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserPublic])
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
    
    user_dict = current_user.model_dump()
    user_dict["id"] = str(user_dict["id"])
    await registrar_auditoria(db, user_dict, "UPDATE_USER", {"target_user_id": user_id, "updated_fields": list(update.keys())})
    
    return UserPublic(**doc)


@router.delete("/{user_id}", status_code=204)
async def deletar_user(
    user_id: str,
    hard: bool = False,
    db=Depends(get_db),
    current_user: UserPublic = Depends(require_roles(Role.ADMIN)),
):
    """Inativa o usuário (soft delete) por padrão, ou exclui fisicamente (hard delete) se hard=True."""
    if hard:
        resultado = await db["users"].delete_one({"_id": ObjectId(user_id)})
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        user_dict = current_user.model_dump()
        user_dict["id"] = str(user_dict["id"])
        await registrar_auditoria(db, user_dict, "EXCLUIR_USER", {"target_user_id": user_id})
    else:
        resultado = await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"situacao": "Inativo"}},
        )
        if resultado.matched_count == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
            
        user_dict = current_user.model_dump()
        user_dict["id"] = str(user_dict["id"])
        await registrar_auditoria(db, user_dict, "INATIVAR_USER", {"target_user_id": user_id})


@router.get("/me/pendencias", status_code=200)
async def listar_minhas_pendencias(
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna as pendências de auditoria/KM morta do motorista logado."""
    doc = await db["users"].find_one({"_id": ObjectId(str(current_user.id))})
    if not doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    perfil = doc.get("perfil_motorista") or {}
    pendencias = perfil.get("pendencias_auditoria") or []
    # Filtra apenas pendências ativas PENDENTEs
    ativas = [p for p in pendencias if isinstance(p, dict) and p.get("status") == "PENDENTE"]
    return ativas


@router.post("/me/pendencias/{pendencia_id}/resolver", status_code=200)
async def resolver_minha_pendencia(
    pendencia_id: str,
    dados: dict,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Resolve a pendência de KM morta (com justificativa com foto ou assinatura/recusa de advertência)."""
    user_id = str(current_user.id)
    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    perfil = doc.get("perfil_motorista") or {}
    pendencias = perfil.get("pendencias_auditoria") or []
    advertencias = perfil.get("advertencias") or []
    
    encontrada = False
    now = datetime.utcnow()
    for p in pendencias:
        if str(p.get("_id") or p.get("id")) == pendencia_id:
            encontrada = True
            tipo_resolucao = dados.get("tipo_resolucao", "JUSTIFICATIVA")
            if tipo_resolucao == "ADVERTENCIA":
                p["status"] = "ADVERTIDO"
                p["assinatura_url"] = dados.get("assinatura_url")
                p["recusou_assinar"] = bool(dados.get("recusou_assinar", False))
                # Adiciona advertência oficial no perfil
                advertencias.append({
                    "_id": ObjectId(),
                    "data": now,
                    "descricao": f"Advertência disciplinar por KM Morta ({p.get('km_morta', 0)} KM) no veículo {p.get('veiculo_placa', '')}",
                    "registrado_por": "SISTEMA",
                    "observacao": "Recusou assinatura" if p["recusou_assinar"] else "Assinada digitalmente no app",
                })
            else:
                p["status"] = "JUSTIFICADO"
                p["foto_justificativa_url"] = dados.get("foto_justificativa_url")
            
            p["data_resolucao"] = now
            break
            
    if not encontrada:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
        
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "perfil_motorista.pendencias_auditoria": pendencias,
            "perfil_motorista.advertencias": advertencias,
        }}
    )
    return {"status": "sucesso", "mensagem": "Pendência resolvida com sucesso"}

