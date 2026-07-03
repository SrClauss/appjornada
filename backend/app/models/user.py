from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BaseModel, BeforeValidator, EmailStr, Field, model_validator
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
    senha: Optional[str] = None
    pin: Optional[str] = None          # PIN de 4 dígitos para abertura de jornada
    perfil_motorista: Optional[PerfilMotorista] = None

    @model_validator(mode="after")
    def validate_password_and_pin(self) -> 'UserCreate':
        if self.role == Role.MOTORISTA:
            if not self.pin:
                raise ValueError("PIN é obrigatório para motoristas")
            if len(self.pin) != 4 or not self.pin.isdigit():
                raise ValueError("PIN deve ter exatamente 4 dígitos numéricos")
        else:
            if not self.senha:
                raise ValueError("Senha é obrigatória para gestores e administradores")
        return self


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
    has_pin: bool = False

    @model_validator(mode="before")
    @classmethod
    def check_pin_hash(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["has_pin"] = bool(data.get("pin_hash"))
        elif hasattr(data, "pin_hash"):
            data.has_pin = bool(getattr(data, "pin_hash"))
        return data

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class User(UserBase):
    """Documento completo armazenado no MongoDB (inclui senha_hash)."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    senha_hash: Optional[str] = None
    pin_hash: Optional[str] = None     # bcrypt do PIN de jornada
    perfil_motorista: Optional[PerfilMotorista] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
