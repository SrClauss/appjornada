from typing import Optional
from pydantic import BaseModel
from .user import Role


class Token(BaseModel):
    """Resposta do endpoint de login."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Payload decodificado do JWT."""
    user_id: Optional[str] = None
    role: Optional[Role] = None
