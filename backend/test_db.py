import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://root:appjornada2024@localhost:27017/?authSource=admin")
    db = client["app_jornada"]
    jornadas = await db.jornadas.find({"status": {"$in": ["ABERTA", "EM_ANDAMENTO", "EM_PAUSA", "PRE_FECHAMENTO"]}}).to_list(100)
    print(f"Jornadas não encerradas: {len(jornadas)}")
    for j in jornadas:
        print(f"ID: {j['_id']}, Motorista: {j.get('motorista_id')}, Status: {j['status']}")

asyncio.run(main())
