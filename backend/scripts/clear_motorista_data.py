import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017/appjornada")
    db = client.get_default_database()
    
    driver = await db["users"].find_one({"email": "motorista@test.com"})
    if not driver:
        print("Motorista não encontrado")
        return
        
    driver_id = driver["_id"]
    print("Driver ID:", driver_id)
    
    res = await db["jornadas"].delete_many({
        "motorista_id": driver_id
    })
    print("Deleted journeys:", res.deleted_count)
    
    res_gps = await db["historico_gps"].delete_many({
        "motorista_id": driver_id
    })
    print("Deleted GPS points:", res_gps.deleted_count)

if __name__ == '__main__':
    asyncio.run(main())
