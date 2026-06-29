from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import criar_access_token, hash_senha, verificar_senha
from app.models.token import Token
from app.models.user import User, UserCreate, UserPublic


async def registrar_usuario(db: AsyncIOMotorDatabase, dados: UserCreate) -> UserPublic:
    existente = await db["users"].find_one({"email": dados.email})
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        )

    doc = dados.model_dump(exclude={"senha", "pin"})
    doc["senha_hash"] = hash_senha(dados.senha)
    doc["pin_hash"] = hash_senha(dados.pin) if dados.pin else None

    if dados.perfil_motorista is not None:
        doc["perfil_motorista"] = dados.perfil_motorista.model_dump(mode="json")
    else:
        doc["perfil_motorista"] = None

    resultado = await db["users"].insert_one(doc)
    criado = await db["users"].find_one({"_id": resultado.inserted_id})
    return UserPublic(**criado)


async def login(db: AsyncIOMotorDatabase, email: str, senha: str) -> Token:
    doc = await db["users"].find_one({"email": email})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    valido = verificar_senha(senha, doc.get("senha_hash"))
    if not valido and doc.get("role") == "MOTORISTA" and doc.get("pin_hash"):
        valido = verificar_senha(senha, doc["pin_hash"])

    if not valido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if doc.get("situacao") != "Ativo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    access_token = criar_access_token(
        data={"sub": str(doc["_id"]), "role": doc["role"]}
    )
    return Token(access_token=access_token)


async def buscar_usuario_por_id(db: AsyncIOMotorDatabase, user_id: str) -> UserPublic:
    from bson import ObjectId

    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return UserPublic(**doc)
