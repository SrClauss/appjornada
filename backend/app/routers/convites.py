from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import hash_senha
from app.models.user import Role, UserPublic

router = APIRouter(prefix="/auth/convites", tags=["convites"])


class GerarConvitePayload(BaseModel):
    role: str = Field(default="ADMIN", description="Papel a ser atribuído: ADMIN, GESTOR ou MOTORISTA")


class AceitarConvitePayload(BaseModel):
    token: str = Field(..., description="Token único do convite")
    nome: str = Field(..., min_length=2, description="Nome completo do convidado")
    email: EmailStr = Field(..., description="E-mail de acesso")
    senha: str = Field(..., min_length=6, description="Senha de acesso")
    confirmacao_senha: str = Field(..., min_length=6, description="Confirmação da senha")
    pin: str | None = Field(default=None, min_length=4, max_length=4, description="PIN de 4 dígitos para motorista")


@router.post("/gerar")
async def gerar_convite(
    payload: GerarConvitePayload,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Gera um novo token de convite para cadastrar um Administrador, Gestor ou Motorista, válido por 24 horas.
    """
    user_role = getattr(current_user, "role", None) if not isinstance(current_user, dict) else current_user.get("role")
    if user_role not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem gerar convites.",
        )

    target_role = payload.role.upper()
    if target_role not in ["ADMIN", "GESTOR", "MOTORISTA"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O papel de convite deve ser ADMIN, GESTOR ou MOTORISTA.",
        )

    token = str(uuid4())
    now = datetime.utcnow()
    expira_em = now + timedelta(hours=24)

    user_email = getattr(current_user, "email", "admin") if not isinstance(current_user, dict) else current_user.get("email")

    doc = {
        "token": token,
        "role": target_role,
        "criado_por": user_email,
        "criado_em": now,
        "expira_em": expira_em,
        "status": "PENDENTE",
    }

    await db["convites_admin"].insert_one(doc)

    invite_url = f"https://minhajornada.lysia.tech/#/registro-admin?token={token}"

    return {
        "sucesso": True,
        "token": token,
        "role": target_role,
        "invite_url": invite_url,
        "expira_em": expira_em.isoformat(),
        "mensagem": f"Convite para {target_role} gerado com sucesso! Válido por 24 horas.",
    }


@router.get("/validar/{token}")
async def validar_convite(token: str, db=Depends(get_db)):
    """
    Valida se o token de convite é válido, pendente e não expirado (< 24h).
    """
    doc = await db["convites_admin"].find_one({"token": token})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado ou inválido.",
        )

    if doc.get("status") != "PENDENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite já foi utilizado.",
        )

    expira_em = doc.get("expira_em")
    if isinstance(expira_em, str):
        expira_em = datetime.fromisoformat(expira_em)

    if expira_em and datetime.utcnow() > expira_em:
        await db["convites_admin"].update_one(
            {"token": token},
            {"$set": {"status": "EXPIRADO"}},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite expirou (validade de 24 horas excedida).",
        )

    return {
        "valido": True,
        "role": doc.get("role", "ADMIN"),
        "expira_em": expira_em.isoformat() if expira_em else None,
        "criado_por": doc.get("criado_por"),
    }


@router.post("/aceitar", status_code=201)
async def aceitar_convite(payload: AceitarConvitePayload, db=Depends(get_db)):
    """
    Consome o convite e registra a conta do novo Administrador/Gestor.
    """
    if payload.senha != payload.confirmacao_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha e a confirmação de senha não coincidem.",
        )

    # Valida o token
    doc = await db["convites_admin"].find_one({"token": payload.token})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado ou inválido.",
        )

    if doc.get("status") != "PENDENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite já foi utilizado ou expirou.",
        )

    expira_em = doc.get("expira_em")
    if isinstance(expira_em, str):
        expira_em = datetime.fromisoformat(expira_em)

    if expira_em and datetime.utcnow() > expira_em:
        await db["convites_admin"].update_one(
            {"token": payload.token},
            {"$set": {"status": "EXPIRADO"}},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este convite expirou (validade de 24 horas excedida).",
        )

    # Verifica se e-mail já está cadastrado
    existente = await db["users"].find_one({"email": payload.email.lower()})
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este endereço de e-mail já está cadastrado no sistema.",
        )

    target_role = doc.get("role", "ADMIN")
    senha_hashed = hash_senha(payload.senha)

    novo_usuario = {
        "nome": payload.nome,
        "email": payload.email.lower(),
        "senha_hash": senha_hashed,
        "role": target_role,
        "pin": payload.pin if target_role == "MOTORISTA" else None,
        "situacao": "Ativo",
        "criado_em": datetime.utcnow(),
    }

    result = await db["users"].insert_one(novo_usuario)

    # Se for MOTORISTA, cadastra também na coleção de motoristas
    if target_role == "MOTORISTA":
        novo_motorista = {
            "user_id": str(result.inserted_id),
            "nome": payload.nome,
            "email": payload.email.lower(),
            "pin": payload.pin or "1234",
            "situacao": "Ativo",
            "criado_em": datetime.utcnow(),
        }
        await db["motoristas"].insert_one(novo_motorista)

    # Invalida o convite
    await db["convites_admin"].update_one(
        {"token": payload.token},
        {
            "$set": {
                "status": "UTILIZADO",
                "utilizado_por": str(result.inserted_id),
                "utilizado_em": datetime.utcnow(),
            }
        },
    )

    return {
        "sucesso": True,
        "mensagem": f"Cadastro de {target_role.lower()} realizado com sucesso!",
        "user_id": str(result.inserted_id),
        "email": payload.email.lower(),
        "role": target_role,
    }
