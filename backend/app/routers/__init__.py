from .auth import router as auth
from .users import router as users
from .veiculos import router as veiculos
from .jornadas import router as jornadas
from .gps import router as gps
from .manutencoes import router as manutencoes
from .metas import router as metas
from .relatorios import router as relatorios
from .uploads import router as uploads
from .coleta import router as coleta
from .precos_particulares import router as precos_particulares

from .metricas import router as metricas

__all__ = [
    "auth",
    "users",
    "veiculos",
    "jornadas",
    "gps",
    "manutencoes",
    "metas",
    "relatorios",
    "uploads",
    "coleta",
    "precos_particulares",
    "metricas",
]
