from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


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


class PerfilMotorista(BaseModel):
    """Subdocumento embutido em User quando role=MOTORISTA."""
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    nivel_id: Optional[str] = None   # ID_NIVEL do Excel
    cnh: Optional[CNH] = None
    dados_bancarios: Optional[DadosBancarios] = None
    limiar_inatividade_minutos: Optional[int] = 15

