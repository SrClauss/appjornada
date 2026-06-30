from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, GEOSPHERE
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client().get_default_database()


async def _tentar_criar_indice(db, colecao: str, keys, **kwargs) -> None:
    """Cria um índice com timeout. Loga aviso se falhar, não interrompe o startup."""
    try:
        await asyncio.wait_for(
            db[colecao].create_index(keys, **kwargs),
            timeout=8.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout ao criar índice em '%s' — será criado sob demanda.", colecao)
    except Exception as exc:
        logger.warning("Falha ao criar índice em '%s': %s", colecao, exc)


async def _criar_indices(db: AsyncIOMotorDatabase) -> None:
    """Garante índices essenciais na inicialização. Operação idempotente."""
    # users — unicidade de e-mail
    await _tentar_criar_indice(db, "users", "email", unique=True)

    # jornadas — busca por motorista+data (query mais comum)
    await _tentar_criar_indice(db, "jornadas", [("motorista_id", ASCENDING), ("data", ASCENDING)])
    # jornadas abertas — dashboard do gestor
    await _tentar_criar_indice(db, "jornadas", "status")

    # historico_gps — série temporal por motorista
    await _tentar_criar_indice(db, "historico_gps", [("motorista_id", ASCENDING), ("timestamp", ASCENDING)])
    # historico_gps — queries geoespaciais (2dsphere obrigatório)
    await _tentar_criar_indice(db, "historico_gps", [("localizacao", GEOSPHERE)])

    # ruas_customizadas — queries geoespaciais (2dsphere obrigatório)
    await _tentar_criar_indice(db, "ruas_customizadas", [("coordenada", GEOSPHERE)])

    # manutencoes — por veículo e data
    await _tentar_criar_indice(db, "manutencoes", [("veiculo_id", ASCENDING), ("entrada", ASCENDING)])

    # corridas uber/99 — upsert sem duplicata
    await _tentar_criar_indice(db, "corridas_uber", "trip_id", unique=True)
    await _tentar_criar_indice(db, "corridas_99", "trip_id", unique=True)
    await _tentar_criar_indice(db, "corridas_particulares", "id_corrida", unique=True)


async def connect_db():
    db = get_db()
    await _criar_indices(db)


async def close_db():
    global _client
    if _client is not None:
        _client.close()
        _client = None
