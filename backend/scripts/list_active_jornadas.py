import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017/appjornada")
    db = client.get_default_database()
    jornadas = await db["jornadas"].find({"status": {"$in": ["ABERTA", "EM_ANDAMENTO"]}}).to_list(None)
    for j in jornadas:
        print(f"Jornada ID: {j['_id']} | Motorista: {j.get('motorista_nome')} ({j.get('motorista_id')}) | Status: {j.get('status')}")

if __name__ == '__main__':
    asyncio.run(main())
