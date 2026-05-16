from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


class MetaBonusBase(BaseModel):
    tipo: str
    referencia: str = "GERAL"
    faixa_minima: Optional[float] = None
    faixa_maxima: Optional[float] = None
    bonus: Optional[float] = None


class MetaBonusCreate(MetaBonusBase):
    pass


class MetaBonusUpdate(BaseModel):
    faixa_minima: Optional[float] = None
    faixa_maxima: Optional[float] = None
    bonus: Optional[float] = None
    referencia: Optional[str] = None


class MetaBonus(MetaBonusBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
