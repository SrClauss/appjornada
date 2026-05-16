from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


# ─── Uber ────────────────────────────────────────────────────────────────────

class UberCorrida(BaseModel):
    """Corrida Uber após deduplicação (uma linha por corrida)."""
    id_viagem: str
    nome_motorista: str
    email_motorista: str
    id_colaborador: str       # FROTA_01 → vincula ao veículo
    origem: str
    destino: str
    inicio: datetime
    fim: datetime
    duracao_minutos: int
    programa: str
    tarifa_base: float = 0.0
    gorjeta: float = 0.0
    pedagio: float = 0.0
    ajuste_tarifa: float = 0.0
    total_bruto: float = 0.0  # tarifa_base + gorjeta + ajuste_tarifa
    total_cobrado: float = 0.0  # inclui pedágio
    metodo_pagamento: str
    url_fatura: Optional[str] = None
    data_importacao: datetime = Field(default_factory=datetime.utcnow)


class UberCorridaDB(UberCorrida):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# ─── 99 ──────────────────────────────────────────────────────────────────────

class NoveNoveCorrida(BaseModel):
    """Corrida 99 (uma linha por corrida)."""
    id_corrida: str
    nome_motorista: str
    centro_custo: str         # VEICULO_01 → vincula ao veículo
    solicitacao: datetime
    origem: str
    destino: str
    distancia_km: float
    duracao_minutos: int
    tarifa_bruta: float
    forma_pagamento: str
    taxa_intermediacao: float
    descontos: float
    valor_liquido: float
    status: str
    data_importacao: datetime = Field(default_factory=datetime.utcnow)


class NoveNoveCorridaDB(NoveNoveCorrida):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# ─── Comparativo ─────────────────────────────────────────────────────────────

class CorridaForaJornada(BaseModel):
    plataforma: str           # "UBER" ou "99"
    id_corrida: str
    inicio: datetime
    fim: Optional[datetime] = None
    origem: str
    destino: str
    valor: float
    motivo: str               # "SEM_JORNADA" | "FORA_DO_HORARIO" | "EM_PAUSA"


class ComparativoMotorista(BaseModel):
    motorista_nome: str
    data: date

    # KM
    jornada_km_rodados: Optional[float] = None
    km_plataformas_99: float = 0.0        # 99 fornece km explícito
    km_plataformas_uber: Optional[float] = None  # Uber não fornece km
    delta_km_99: Optional[float] = None   # jornada_km - km_99 (restante = Uber + km morta)

    # Faturamento
    faturamento_uber_declarado: float = 0.0    # o que o motorista lançou na jornada
    faturamento_99_declarado: float = 0.0
    faturamento_uber_relatorio: float = 0.0    # o que o relatório Uber mostra
    faturamento_99_relatorio: float = 0.0
    delta_uber: float = 0.0
    delta_99: float = 0.0

    # Corridas
    total_corridas_uber: int = 0
    total_corridas_99: int = 0
    corridas_fora_jornada: List[CorridaForaJornada] = []

    # Jornada CLT
    horas_trabalhadas: Optional[float] = None
    status_jornada: Optional[str] = None

    # Alertas
    alertas: List[str] = []


class ComparativoResponse(BaseModel):
    data: date
    total_motoristas: int
    motoristas: List[ComparativoMotorista]
