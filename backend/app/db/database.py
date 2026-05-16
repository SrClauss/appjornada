from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, GEOSPHERE

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client().get_default_database()


async def _criar_indices(db: AsyncIOMotorDatabase) -> None:
    """Garante índices essenciais na inicialização. Operação idempotente."""
    # users — unicidade de e-mail
    await db["users"].create_index("email", unique=True, background=True)

    # jornadas — busca por motorista+data (query mais comum)
    await db["jornadas"].create_index(
        [("motorista_id", ASCENDING), ("data", ASCENDING)],
        background=True,
    )
    # jornadas abertas — dashboard do gestor
    await db["jornadas"].create_index("status", background=True)

    # historico_gps — série temporal por motorista
    await db["historico_gps"].create_index(
        [("motorista_id", ASCENDING), ("timestamp", ASCENDING)],
        background=True,
    )
    # historico_gps — queries geoespaciais (2dsphere obrigatório)
    await db["historico_gps"].create_index(
        [("localizacao", GEOSPHERE)],
        background=True,
    )

    # manutencoes — por veículo e data
    await db["manutencoes"].create_index(
        [("veiculo_id", ASCENDING), ("entrada", ASCENDING)],
        background=True,
    )

    # corridas uber/99 — upsert sem duplicata
    await db["corridas_uber"].create_index("trip_id", unique=True, background=True)
    await db["corridas_99"].create_index("trip_id", unique=True, background=True)


async def connect_db():
    db = get_db()
    await _criar_indices(db)


async def close_db():
    global _client
    if _client is not None:
        _client.close()
        _client = None
