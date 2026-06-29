import os
import asyncio
from datetime import datetime, date, time, timedelta, timezone
from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import pytz

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/appjornada")

async def get_route(http_client, from_lon, from_lat, to_lon, to_lat):
    for base_url in [os.getenv("OSRM_URL", "http://osrm:5000"), "http://localhost:5000"]:
        try:
            r = await http_client.get(
                f"{base_url}/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=full&geometries=geojson",
                timeout=3.0
            )
            if r.status_code == 200:
                res_json = r.json()
                if "routes" in res_json and len(res_json["routes"]) > 0:
                    return res_json["routes"][0]["geometry"]["coordinates"]
        except Exception:
            pass
    # Fallback linear interpolation
    num_points = 50
    coords = []
    for i in range(num_points):
        t = i / (num_points - 1)
        lon = from_lon + t * (to_lon - from_lon)
        lat = from_lat + t * (to_lat - from_lat)
        coords.append([lon, lat])
    return coords

async def main():
    print(f"Conectando ao MongoDB em {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()

    local_tz = pytz.timezone("America/Sao_Paulo")
    today = datetime.now(local_tz).date()

    motorista_id = ObjectId("6a3ff9067110907bfff38f53") # Marcos Santos
    placa = "CCC-3C33"

    print("Removendo dados antigos da jornada de hoje...")
    jornada_id = f"MarcosSantos-CCC3C33-{today.strftime('%Y%m%d')}"
    await db["jornadas"].delete_many({"_id": jornada_id})
    await db["historico_gps"].delete_many({"jornada_id": jornada_id})

    # Coordenadas
    lon_carapina, lat_carapina = -40.2694, -20.2446
    lon_rodoviaria, lat_rodoviaria = -40.3444, -20.3204

    async with httpx.AsyncClient() as http_client:
        route_go = await get_route(http_client, lon_carapina, lat_carapina, lon_rodoviaria, lat_rodoviaria)
        route_back = await get_route(http_client, lon_rodoviaria, lat_rodoviaria, lon_carapina, lat_carapina)

    start_dt = local_tz.localize(datetime.combine(today, time(8, 0, 0)))
    current_dt = start_dt

    gps_points = []
    
    # 1. Check-in (08:00)
    current_dt += timedelta(seconds=15)
    
    # Driving first half (08:00 - 12:00) -> 4 hours -> 960 points at 15s intervals
    # We will generate coordinates by walking along the routes back and forth
    full_route = []
    for i in range(12): # 12 trips back and forth
        if i % 2 == 0:
            full_route.extend(route_go)
        else:
            full_route.extend(route_back)

    total_points = 960
    for i in range(total_points):
        route_idx = int((i / (total_points - 1)) * (len(full_route) - 1))
        lon, lat = full_route[route_idx]
        gps_points.append({
            "timestamp": current_dt.astimezone(timezone.utc),
            "motorista_id": motorista_id,
            "jornada_id": jornada_id,
            "localizacao": {"type": "Point", "coordinates": [lon, lat]}
        })
        current_dt += timedelta(seconds=15)

    # 2. Almoço (12:00 - 13:00) -> 1 hour
    # Driver stays in Rodoviaria during lunch
    lon, lat = lon_rodoviaria, lat_rodoviaria
    for _ in range(240): # 240 points at 15s intervals
        gps_points.append({
            "timestamp": current_dt.astimezone(timezone.utc),
            "motorista_id": motorista_id,
            "jornada_id": jornada_id,
            "localizacao": {"type": "Point", "coordinates": [lon, lat]}
        })
        current_dt += timedelta(seconds=15)

    # 3. Retorno Almoço (13:00)
    # Driving second half (13:00 - 17:00) -> 4 hours -> 960 points
    for i in range(12):
        if i % 2 == 0:
            full_route.extend(route_back)
        else:
            full_route.extend(route_go)

    for i in range(total_points):
        route_idx = int((i / (total_points - 1)) * (len(full_route) - 1))
        lon, lat = full_route[route_idx]
        gps_points.append({
            "timestamp": current_dt.astimezone(timezone.utc),
            "motorista_id": motorista_id,
            "jornada_id": jornada_id,
            "localizacao": {"type": "Point", "coordinates": [lon, lat]}
        })
        current_dt += timedelta(seconds=15)

    # Inserir pontos de GPS
    if gps_points:
        await db["historico_gps"].insert_many(gps_points)
        print(f"Inseridos {len(gps_points)} pontos de GPS!")

    # Inserir documento da Jornada
    jornada = {
        "_id": jornada_id,
        "motorista_id": motorista_id,
        "veiculo_id": placa,
        "data": today.isoformat(),
        "status": "FINALIZADA",
        "km_inicial": 20000.0,
        "km_final": 20180.0,
        "foto_odometro_inicial_url": "https://placehold.co/600x400?text=Odometro+Inicial",
        "foto_odometro_final_url": "https://placehold.co/600x400?text=Odometro+Final",
        "eventos": [
            {"tipo": "INICIO_JORNADA", "timestamp": start_dt.astimezone(timezone.utc), "km": 20000.0},
            {"tipo": "INICIO_INTERVALO", "timestamp": (start_dt + timedelta(hours=4)).astimezone(timezone.utc), "km": 20090.0},
            {"tipo": "FIM_INTERVALO", "timestamp": (start_dt + timedelta(hours=5)).astimezone(timezone.utc), "km": 20090.0},
            {"tipo": "FIM_JORNADA", "timestamp": (start_dt + timedelta(hours=9)).astimezone(timezone.utc), "km": 20180.0}
        ],
        "created_at": datetime.now(timezone.utc)
    }

    await db["jornadas"].insert_one(jornada)
    print("Documento da Jornada criado com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())