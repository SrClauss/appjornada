import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from bson import json_util

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017/appjornada")
    db = client.get_default_database()
    users = await db["users"].find().to_list(10)
    for u in users:
        print(json_util.dumps(u, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
