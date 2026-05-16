from datetime import date, time
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId


class Localizacao(BaseModel):
    lat: float
    lon: float


class KmJornada(BaseModel):
    inicial: Optional[float] = None
    final: Optional[float] = None
    rodados: Optional[float] = None
    morta: Optional[float] = 0.0


class HorarioJornada(BaseModel):
    inicio: Optional[time] = None
    fim: Optional[time] = None
    total_horas_segundos: Optional[int] = None


class FotosJornada(BaseModel):
    km_inicial_url: Optional[str] = None
    km_final_url: Optional[str] = None


class Faturamento(BaseModel):
    uber: Optional[float] = 0.0
    noventa_nove: Optional[float] = 0.0
    outros: Optional[float] = 0.0
    total_dia: Optional[float] = 0.0
    comprovante_uber_url: Optional[str] = None
    comprovante_99_url: Optional[str] = None
    comprovante_outros_url: Optional[str] = None


class Pausa(BaseModel):
    id: str
    tipo: str = "PAUSA_MOTORISTA"
    inicio: Optional[time] = None
    fim: Optional[time] = None
    duracao_segundos: Optional[int] = None
    localizacao_inicio: Optional[Localizacao] = None
    localizacao_fim: Optional[Localizacao] = None


class Abastecimento(BaseModel):
    id: str
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    duracao_segundos: Optional[int] = None
    km: Optional[float] = None
    localizacao: Optional[Localizacao] = None
    valor_gnv: Optional[float] = 0.0
    valor_gasolina: Optional[float] = 0.0
    valor_etanol: Optional[float] = 0.0
    foto_comprovante_url: Optional[str] = None


class Sinistro(BaseModel):
    id: str
    hora: Optional[time] = None
    localizacao: Optional[Localizacao] = None
    tipo: Optional[str] = None
    descricao: Optional[str] = None
    imagens_urls: List[str] = []
    boletim_url: Optional[str] = None


class JornadaBase(BaseModel):
    data: Optional[date] = None
    motorista_id: PyObjectId
    veiculo_id: str
    status: str = "ABERTA"
    km: Optional[KmJornada] = None
    localizacao_inicial: Optional[Localizacao] = None
    localizacao_final: Optional[Localizacao] = None
    horario: Optional[HorarioJornada] = None
    fotos: Optional[FotosJornada] = None
    faturamento: Optional[Faturamento] = None
    # ─── CLT ────────────────────────────────────────────────────
    jornada_diaria_clt: float = 8.0      # horas de referência diária
    jornada_semanal_clt: float = 44.0   # horas de referência semanal
    jornada_mensal_clt: float = 220.0   # horas de referência mensal
    saldo_horas_dia: Optional[float] = None  # diferença em horas (negativo = devendo)
    # ─── Acumulados ─────────────────────────────────────────────
    bonus_dia: Optional[float] = 0.0
    faturamento_acumulado_semana: Optional[float] = None
    bonus_acumulado_semana: Optional[float] = None
    faturamento_acumulado_mes: Optional[float] = None
    bonus_acumulado_mes: Optional[float] = None
    # ─── Outros ─────────────────────────────────────────────────
    observacoes: Optional[str] = None
    uso_pessoal: Optional[bool] = False
    comprovante_uso_pessoal_url: Optional[str] = None
    justificativa_uso_pessoal: Optional[str] = None


class JornadaCreate(JornadaBase):
    pass


class JornadaUpdate(BaseModel):
    status: Optional[str] = None
    km: Optional[KmJornada] = None
    horario: Optional[HorarioJornada] = None
    fotos: Optional[FotosJornada] = None
    faturamento: Optional[Faturamento] = None
    bonus_dia: Optional[float] = None
    observacoes: Optional[str] = None
    pausas: Optional[List[Pausa]] = None
    abastecimentos: Optional[List[Abastecimento]] = None
    sinistros: Optional[List[Sinistro]] = None


class Jornada(JornadaBase):
    id: str = Field(..., alias="_id")
    pin: Optional[str] = None  # DIGITAR_PIN — gravado na abertura
    pausas: List[Pausa] = []
    abastecimentos: List[Abastecimento] = []
    sinistros: List[Sinistro] = []

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }
