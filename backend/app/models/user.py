from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BaseModel, BeforeValidator, EmailStr, Field
from bson import ObjectId
from .base import PyObjectId
from .motorista import PerfilMotorista


def _to_str(v: Any) -> str:
    return str(v)


class Role(str, Enum):
    MOTORISTA = "MOTORISTA"
    GESTOR = "GESTOR"
    ADMIN = "ADMIN"


class UserBase(BaseModel):
    nome: str
    email: EmailStr
    role: Role
    situacao: str = "Ativo"


class UserCreate(UserBase):
    senha: str
    pin: Optional[str] = None          # PIN de 4 dígitos para abertura de jornada
    perfil_motorista: Optional[PerfilMotorista] = None


class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    situacao: Optional[str] = None
    role: Optional[Role] = None
    perfil_motorista: Optional[PerfilMotorista] = None
    senha: Optional[str] = None
    pin: Optional[str] = None          # permite trocar o PIN


class UserPublic(UserBase):
    """Resposta segura — nunca expõe senha_hash."""
    id: Annotated[str, BeforeValidator(_to_str)] = Field(alias="_id")
    perfil_motorista: Optional[PerfilMotorista] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class User(UserBase):
    """Documento completo armazenado no MongoDB (inclui senha_hash)."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    senha_hash: str
    pin_hash: Optional[str] = None     # bcrypt do PIN de jornada
    perfil_motorista: Optional[PerfilMotorista] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
