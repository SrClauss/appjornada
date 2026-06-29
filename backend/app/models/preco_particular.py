from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId

class PrecoParticular(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    nome: str
    hora_inicio: str  # "HH:MM", ex: "06:00"
    hora_fim: str  # "HH:MM", ex: "18:00"
    preco_km: float
    preco_minuto: float

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
