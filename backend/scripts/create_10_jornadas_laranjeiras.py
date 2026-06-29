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

    motorista_id = ObjectId("6a3ff9067110907bfff38f52") # Bruno Souza
    placa = "BBB-2B22"

    # Coordinates around Laranjeiras, Serra
    lon_laranjeiras, lat_laranjeiras = -40.258, -20.178
    lon_manguinhos, lat_manguinhos = -40.215, -20.188
    lon_carapina, lat_carapina = -40.269, -20.244

    async with httpx.AsyncClient() as http_client:
        route_go = await get_route(http_client, lon_laranjeiras, lat_laranjeiras, lon_manguinhos, lat_manguinhos)
        route_back = await get_route(http_client, lon_manguinhos, lat_manguinhos, lon_laranjeiras, lat_laranjeiras)
        route_carapina = await get_route(http_client, lon_laranjeiras, lat_laranjeiras, lon_carapina, lat_carapina)

    print("Gerando 10 jornadas históricas para Laranjeiras...")
    for day_offset in range(10):
        target_date = today - timedelta(days=day_offset)
        jornada_id = f"BrunoSouza-BBB2B22-{target_date.strftime('%Y%m%d')}"

        # Clean old run
        await db["jornadas"].delete_many({"_id": jornada_id})
        await db["historico_gps"].delete_many({"jornada_id": jornada_id})

        start_dt = local_tz.localize(datetime.combine(target_date, time(8, 30, 0)))
        current_dt = start_dt
        km_inicial = 15000.0 + (9 - day_offset) * 110.0
        km_final = km_inicial + 110.0

        gps_points = []
        full_route = route_go + route_back + route_carapina
        
        # Generate GPS telemetry points at intervals
        total_points = 500
        for i in range(total_points):
            route_idx = int((i / (total_points - 1)) * (len(full_route) - 1))
            lon, lat = full_route[route_idx]
            
            point_dt = start_dt + timedelta(seconds=i * 60) # 1-minute intervals for historical optimization
            gps_points.append({
                "timestamp": point_dt.astimezone(timezone.utc),
                "motorista_id": motorista_id,
                "jornada_id": jornada_id,
                "localizacao": {"type": "Point", "coordinates": [lon, lat]}
            })

        if gps_points:
            await db["historico_gps"].insert_many(gps_points)

        # Insert journey doc
        jornada = {
            "_id": jornada_id,
            "motorista_id": motorista_id,
            "veiculo_id": placa,
            "data": target_date.isoformat(),
            "status": "FINALIZADA",
            "km_inicial": km_inicial,
            "km_final": km_final,
            "foto_odometro_inicial_url": "https://placehold.co/600x400?text=Odometro+Inicial",
            "foto_odometro_final_url": "https://placehold.co/600x400?text=Odometro+Final",
            "eventos": [
                {"tipo": "INICIO_JORNADA", "timestamp": start_dt.astimezone(timezone.utc), "km": km_inicial},
                {"tipo": "INICIO_INTERVALO", "timestamp": (start_dt + timedelta(hours=4)).astimezone(timezone.utc), "km": km_inicial + 50.0},
                {"tipo": "FIM_INTERVALO", "timestamp": (start_dt + timedelta(hours=5)).astimezone(timezone.utc), "km": km_inicial + 50.0},
                {"tipo": "FIM_JORNADA", "timestamp": (start_dt + timedelta(hours=8.5)).astimezone(timezone.utc), "km": km_final}
            ],
            "created_at": datetime.now(timezone.utc)
        }
        await db["jornadas"].insert_one(jornada)
        print(f"  Jornada {jornada_id} criada com {len(gps_points)} pontos de telemetria.")

if __name__ == "__main__":
    asyncio.run(main())