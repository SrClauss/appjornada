from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


class CNH(BaseModel):
    vencimento: Optional[date] = None
    imagem_url: Optional[str] = None


class DadosBancarios(BaseModel):
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    operador: Optional[str] = None
    cnpj: Optional[str] = None
    empresa: Optional[str] = None


class Advertencia(BaseModel):
    """Advertência disciplinar (escrita) embutida no perfil do motorista."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    data: datetime = Field(default_factory=datetime.utcnow)
    descricao: str
    registrado_por: Optional[str] = None  # _id do gestor/admin
    observacao: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class AdvertenciaCreate(BaseModel):
    descricao: str
    data: Optional[datetime] = None
    observacao: Optional[str] = None


class PendenciaAuditoria(BaseModel):
    """Pendência de auditoria/KM morta vinculada ao motorista."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    data_criacao: datetime = Field(default_factory=datetime.utcnow)
    veiculo_id: Optional[str] = None
    veiculo_placa: Optional[str] = None
    jornada_origem_id: Optional[str] = None
    km_morta: float = 0.0
    status: str = "PENDENTE"  # PENDENTE, JUSTIFICADO, ADVERTIDO
    tipo: str = "KM_MORTA"
    descricao: str = "Uso indevido ou não declarado de veículo (KM Morta)"
    foto_justificativa_url: Optional[str] = None
    assinatura_url: Optional[str] = None
    recusou_assinar: bool = False
    data_resolucao: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


class ResolverPendenciaRequest(BaseModel):
    tipo_resolucao: str  # "JUSTIFICATIVA" ou "ADVERTENCIA"
    foto_justificativa_url: Optional[str] = None
    assinatura_url: Optional[str] = None
    recusou_assinar: bool = False


class PerfilMotorista(BaseModel):
    """Subdocumento embutido em User quando role=MOTORISTA."""
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    nivel_id: Optional[str] = None   # ID_NIVEL do Excel
    cnh: Optional[CNH] = None
    dados_bancarios: Optional[DadosBancarios] = None
    advertencias: List[Advertencia] = Field(default_factory=list)
    pendencias_auditoria: List[PendenciaAuditoria] = Field(default_factory=list)
    limiar_inatividade_minutos: Optional[int] = 15

