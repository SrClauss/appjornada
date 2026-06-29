import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017/appjornada")
    db = client.get_default_database()
    users = await db["users"].find().to_list(None)
    for u in users:
        print(f"Nome: {u.get('nome')} | Email: {u.get('email')} | Role: {u.get('role')} | Status: {u.get('situacao')}")

if __name__ == '__main__':
    asyncio.run(main())
