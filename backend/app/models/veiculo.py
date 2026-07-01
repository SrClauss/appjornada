from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


class VeiculoBase(BaseModel):
    id_placa: str = Field(..., description="Placa do veículo, usada como _id")
    marca_modelo: Optional[str] = None
    ano_modelo: Optional[str] = None
    cor: Optional[str] = None
    situacao: str = "RODANDO"
    km_atual: Optional[float] = None
    vencimento_ipva: Optional[date] = None
    imagem_clrv_url: Optional[str] = None
    foto_veiculo_url: Optional[str] = None
    custo_manutencao_por_km: Optional[float] = 0.0
    custo_depreciacao_por_km: Optional[float] = 0.0


class VeiculoCreate(VeiculoBase):
    pass


class VeiculoUpdate(BaseModel):
    marca_modelo: Optional[str] = None
    ano_modelo: Optional[str] = None
    cor: Optional[str] = None
    situacao: Optional[str] = None
    km_atual: Optional[float] = None
    vencimento_ipva: Optional[date] = None
    imagem_clrv_url: Optional[str] = None
    foto_veiculo_url: Optional[str] = None
    custo_manutencao_por_km: Optional[float] = None
    custo_depreciacao_por_km: Optional[float] = None


class Veiculo(VeiculoBase):
    id: str = Field(alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
