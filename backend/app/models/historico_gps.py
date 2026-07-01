from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class HistoricoGPSBase(BaseModel):
    """
    Usar MongoDB Time Series Collection:
      timeseries: { timeField: 'timestamp', metaField: 'motorista_id' }
    Índice: { localizacao: '2dsphere' } para queries geoespaciais.
    """
    timestamp: Optional[datetime] = None
    motorista_id: PyObjectId
    jornada_id: Optional[str] = None
    localizacao: GeoPoint
    distancia_ultima_m: Optional[float] = None
    status: Optional[str] = None
    rua: Optional[str] = None


class HistoricoGPSCreate(HistoricoGPSBase):
    pass


class HistoricoGPS(HistoricoGPSBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class HistoricoGPSBatchItem(BaseModel):
    timestamp: datetime
    localizacao: GeoPoint
    distancia_ultima_m: Optional[float] = None
    status: Optional[str] = None


class HistoricoGPSBatch(BaseModel):
    motorista_id: PyObjectId
    jornada_id: str
    pontos: list[HistoricoGPSBatchItem]

