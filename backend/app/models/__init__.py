from .base import PyObjectId
from .motorista import CNH, DadosBancarios, PerfilMotorista
from .user import Role, User, UserCreate, UserUpdate, UserPublic
from .token import Token, TokenData
from .veiculo import Veiculo, VeiculoCreate, VeiculoUpdate
from .jornada import (
    Jornada, JornadaCreate, JornadaUpdate,
    Pausa, Abastecimento, Sinistro, Localizacao,
)
from .manutencao import Manutencao, ManutencaoCreate, ManutencaoUpdate
from .historico_gps import HistoricoGPS, HistoricoGPSCreate, GeoPoint
from .meta_bonus import MetaBonus, MetaBonusCreate, MetaBonusUpdate

__all__ = [
    # base
    "PyObjectId",
    # motorista (subdocumentos)
    "CNH", "DadosBancarios", "PerfilMotorista",
    # user + auth
    "Role", "User", "UserCreate", "UserUpdate", "UserPublic",
    "Token", "TokenData",
    # veículo
    "Veiculo", "VeiculoCreate", "VeiculoUpdate",
    # jornada + subdocs embutidos
    "Jornada", "JornadaCreate", "JornadaUpdate",
    "Pausa", "Abastecimento", "Sinistro", "Localizacao",
    # manutenção
    "Manutencao", "ManutencaoCreate", "ManutencaoUpdate",
    # GPS time-series
    "HistoricoGPS", "HistoricoGPSCreate", "GeoPoint",
    # metas e bônus
    "MetaBonus", "MetaBonusCreate", "MetaBonusUpdate",
]
