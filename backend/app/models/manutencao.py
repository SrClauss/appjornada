from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId
from .jornada import Localizacao


class Servico(BaseModel):
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    foto_nf_url: Optional[str] = None


class ManutencaoBase(BaseModel):
    jornada_id: Optional[str] = None
    motorista_id: Optional[PyObjectId] = None
    veiculo_id: str
    entrada: Optional[datetime] = None
    saida: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    localizacao: Optional[Localizacao] = None
    decisao: Optional[str] = None
    km: Optional[float] = None
    km_proxima_revisao: Optional[float] = None
    status: str = "EM_ANDAMENTO"
    oficina: Optional[str] = None
    servico: Optional[Servico] = None


class ManutencaoCreate(ManutencaoBase):
    pass


class ManutencaoUpdate(BaseModel):
    saida: Optional[datetime] = None
    duracao_minutos: Optional[int] = None
    decisao: Optional[str] = None
    km: Optional[float] = None
    km_proxima_revisao: Optional[float] = None
    status: Optional[str] = None
    oficina: Optional[str] = None
    servico: Optional[Servico] = None


class Manutencao(ManutencaoBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
