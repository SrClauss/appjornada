import asyncio
from app.db.database import get_db

async def fix():
    db = get_db()
    new_base = {
        "nome": "Base de Operações - Rua Laura Crespo Maia",
        "cidade": "São Mateus",
        "estado": "ES",
        "lat": -18.71439200,
        "lon": -39.82804900,
        "zoom_padrao": 15,
        "is_principal": True
    }
    
    await db["bases_operacao"].delete_many({})
    await db["bases_operacao"].insert_one(new_base)
    print("✅ Base de Operações atualizada com 8 decimais de precisão (-18.71439200, -39.82804900)")

asyncio.run(fix())
