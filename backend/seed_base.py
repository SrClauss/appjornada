import asyncio
from app.db.database import get_db

async def seed_base():
    db = get_db()
    base_sao_mateus = {
        "id": "base-sao-mateus-central",
        "nome": "Base de Operações São Mateus",
        "cidade": "São Mateus",
        "estado": "ES",
        "lat": -18.7214,
        "lon": -39.8551,
        "zoom_padrao": 14,
        "is_principal": True
    }
    await db["bases_operacao"].update_one(
        {"id": base_sao_mateus["id"]},
        {"$set": base_sao_mateus},
        upsert=True
    )
    print("✅ Base de Operações São Mateus cadastrada como Principal!")

if __name__ == "__main__":
    asyncio.run(seed_base())
