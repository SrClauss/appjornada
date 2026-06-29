import os
import asyncio
import math
from datetime import datetime, date, time, timedelta, timezone
from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import pytz

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/appjornada")

# 7 safe Vitória/Serra coordinates
POOLS = {
    "laranjeiras": [-40.2497, -20.1794],     # Av. Civit I, Laranjeiras (Serra)
    "carapina": [-40.2695, -20.2446],        # Rod. BR-101, Carapina (Serra)
    "jardim_camburi": [-40.2678, -20.2646],  # Av. Dante Michelini, Jardim Camburi (Vitória)
    "praia_do_canto": [-40.2947, -20.2995],  # Av. Américo Buaiz, Praia do Canto (Vitória)
    "ufes": [-40.3015, -20.2762],            # Av. Fernando Ferrari, Ufes (Vitória)
    "centro_vitoria": [-40.3350, -20.3190],  # Av. Jerônimo Monteiro, Centro (Vitória)
    "rodoviaria": [-40.3444, -20.3204]       # Av. Alexandre Buaiz, Rodoviária (Vitória)
}

def haversine_distance(p1, p2):
    lon1, lat1 = p1
    lon2, lat2 = p2
    R = 6371000.0 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

# Dictionary to cache routes: key = (from_loc, to_loc), value = (coords_with_streets, duration_sec)
route_cache = {}

async def get_osrm_route(http_client, from_coord, to_coord, retries=3):
    from_lon, from_lat = from_coord
    to_lon, to_lat = to_coord
    
    if from_coord == to_coord:
        return [([from_lon, from_lat], "Via Local")], 0.0
    
    # Try local OSRM first, fallback to container name osrm
    for base_url in [os.getenv("OSRM_URL", "http://osrm:5000"), "http://localhost:5000"]:
        for attempt in range(retries):
            try:
                r = await http_client.get(
                    f"{base_url}/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}?overview=full&geometries=geojson&steps=true",
                    timeout=5.0
                )
                if r.status_code == 200:
                    res_json = r.json()
                    if "routes" in res_json and len(res_json["routes"]) > 0:
                        route = res_json["routes"][0]
                        legs = route["legs"]
                        
                        coords_with_streets = []
                        for leg in legs:
                            for step in leg["steps"]:
                                street_name = step.get("name", "").strip()
                                if not street_name:
                                    street_name = "Via Local"
                                step_coords = step["geometry"]["coordinates"]
                                for c in step_coords:
                                    coords_with_streets.append((c, street_name))
                                    
                        duration_sec = float(route["duration"])
                        return coords_with_streets, duration_sec
            except Exception:
                pass
            await asyncio.sleep(0.2)
            
    # Fallback route
    print(f"Fallback OSRM route for {from_coord} to {to_coord}")
    num_points = 50
    coords_with_streets = []
    for i in range(num_points):
        t = i / (num_points - 1)
        lon = from_lon + t * (to_lon - from_lon)
        lat = from_lat + t * (to_lat - from_lat)
        coords_with_streets.append(([lon, lat], "Rodovia do Sol"))
    return coords_with_streets, 600.0

async def prefetch_all_routes(http_client):
    print("Prefetching OSRM routes for all pool pairs...")
    tasks = []
    keys = []
    for from_name, from_coord in POOLS.items():
        for to_name, to_coord in POOLS.items():
            keys.append((from_name, to_name))
            if from_name == to_name:
                route_cache[(from_name, to_name)] = ([(from_coord, "Via Local")], 0.0)
            else:
                tasks.append(get_osrm_route(http_client, from_coord, to_coord))
            
    results = await asyncio.gather(*tasks, return_exceptions=True)
    non_local_keys = [k for k in keys if k[0] != k[1]]
    for key, res in zip(non_local_keys, results):
        if isinstance(res, Exception):
            print(f"Error prefetching route for {key}: {res}")
            # Fallback
            from_coord = POOLS[key[0]]
            to_coord = POOLS[key[1]]
            num_points = 50
            coords_with_streets = []
            for i in range(num_points):
                t = i / (num_points - 1)
                lon = from_coord[0] + t * (to_coord[0] - from_coord[0])
                lat = from_coord[1] + t * (to_coord[1] - from_coord[1])
                coords_with_streets.append(([lon, lat], "Rodovia do Sol"))
            route_cache[key] = (coords_with_streets, 600.0)
        else:
            route_cache[key] = res
    print(f"Prefetched {len(route_cache)} routes into cache.")

async def generate_journey_for_sequence(
    db, motorista, veiculo_id, target_date, start_time_str, route_sequence
):
    local_tz = pytz.timezone("America/Sao_Paulo")
    start_hour, start_min = map(int, start_time_str.split(":"))
    current_dt = local_tz.localize(datetime.combine(target_date, time(start_hour, start_min, 0)))
    
    jornada_id = f"{motorista['nome'].replace(' ', '')}-{veiculo_id}-{target_date.strftime('%Y%m%d')}"
    
    await db["jornadas"].delete_many({"_id": jornada_id})
    await db["historico_gps"].delete_many({"jornada_id": jornada_id})
    
    gps_points = []
    events = []
    
    km_current = 20000.0 + (int(target_date.strftime('%d')) * 85.0)
    km_inicial = km_current
    
    # 1. Inicio da jornada
    events.append({
        "tipo": "INICIO_JORNADA",
        "timestamp": current_dt.astimezone(timezone.utc),
        "km": km_current
    })
    
    driving_seconds_accum = 0
    seq_idx = 0
    current_loc_name = route_sequence[0]
    
    # Exatamente 8 horas de conducao (28800s)
    target_driving_seconds = 28800
    
    lunch_done = False
    refuel_done = False
    
    while driving_seconds_accum < target_driving_seconds:
        seq_idx = (seq_idx + 1) % len(route_sequence)
        next_loc_name = route_sequence[seq_idx]
        
        # Get cached route
        coords_with_streets, duration_sec = route_cache[(current_loc_name, next_loc_name)]
        route_coords = [item[0] for item in coords_with_streets]
        
        # Distancia via haversine
        distance_m = sum(haversine_distance(route_coords[i-1], route_coords[i]) for i in range(1, len(route_coords)))
        
        # Truncar se estourar
        remaining_driving = target_driving_seconds - driving_seconds_accum
        if duration_sec > remaining_driving:
            ratio = remaining_driving / duration_sec
            duration_sec = remaining_driving
            distance_m = distance_m * ratio
            
            target_dist = distance_m
            cum_dist = 0.0
            truncated_coords_with_streets = [coords_with_streets[0]]
            for i in range(1, len(coords_with_streets)):
                d = haversine_distance(coords_with_streets[i-1][0], coords_with_streets[i][0])
                if cum_dist + d >= target_dist:
                    t = (target_dist - cum_dist) / d
                    lon = coords_with_streets[i-1][0][0] + t * (coords_with_streets[i][0][0] - coords_with_streets[i-1][0][0])
                    lat = coords_with_streets[i-1][0][1] + t * (coords_with_streets[i][0][1] - coords_with_streets[i-1][0][1])
                    truncated_coords_with_streets.append(([lon, lat], coords_with_streets[i][1]))
                    break
                truncated_coords_with_streets.append(coords_with_streets[i])
                cum_dist += d
            coords_with_streets = truncated_coords_with_streets
            route_coords = [item[0] for item in coords_with_streets]
            
        # Gerar pontos a cada 15 segundos
        steps = max(2, int(duration_sec / 15))
        step_distance_m = distance_m / steps
        
        cum_distances = [0.0]
        for i in range(1, len(route_coords)):
            cum_distances.append(cum_distances[-1] + haversine_distance(route_coords[i-1], route_coords[i]))
            
        for p_idx in range(steps):
            target_cum_dist = p_idx * step_distance_m
            
            idx = 1
            while idx < len(route_coords) and cum_distances[idx] < target_cum_dist:
                idx += 1
            if idx >= len(route_coords):
                idx = len(route_coords) - 1
                
            d_prev = cum_distances[idx-1]
            d_curr = cum_distances[idx]
            segment_len = d_curr - d_prev
            
            if segment_len > 0:
                t = (target_cum_dist - d_prev) / segment_len
                lon = route_coords[idx-1][0] + t * (route_coords[idx][0] - route_coords[idx-1][0])
                lat = route_coords[idx-1][1] + t * (route_coords[idx][1] - route_coords[idx-1][1])
            else:
                lon, lat = route_coords[idx]
                
            dt_step = duration_sec / steps
            current_dt += timedelta(seconds=dt_step)
            
            rua = coords_with_streets[idx-1][1]
            
            gps_points.append({
                "timestamp": current_dt.astimezone(timezone.utc),
                "motorista_id": motorista["_id"],
                "jornada_id": jornada_id,
                "localizacao": {"type": "Point", "coordinates": [lon, lat]},
                "distancia_ultima_m": step_distance_m,
                "status": "CONDUZINDO",
                "rua": rua
            })
            
        km_current += distance_m / 1000.0
        driving_seconds_accum += duration_sec
        current_loc_name = next_loc_name
        
        # Almoço: 1 hora apos 4 horas de conducao
        if not lunch_done and driving_seconds_accum >= 14400:
            events.append({
                "tipo": "INICIO_INTERVALO",
                "timestamp": current_dt.astimezone(timezone.utc),
                "km": km_current
            })
            for _ in range(240):
                current_dt += timedelta(seconds=15)
                gps_points.append({
                    "timestamp": current_dt.astimezone(timezone.utc),
                    "motorista_id": motorista["_id"],
                    "jornada_id": jornada_id,
                    "localizacao": {"type": "Point", "coordinates": route_coords[-1]},
                    "distancia_ultima_m": 0.0,
                    "status": "PARADO",
                    "rua": coords_with_streets[-1][1]
                })
            events.append({
                "tipo": "FIM_INTERVALO",
                "timestamp": current_dt.astimezone(timezone.utc),
                "km": km_current
            })
            lunch_done = True
            
        # Abastecimento: 10 min apos 7.5 horas de conducao
        if not refuel_done and driving_seconds_accum >= 27000:
            events.append({
                "tipo": "ABASTECIMENTO",
                "timestamp": current_dt.astimezone(timezone.utc),
                "km": km_current
            })
            for _ in range(40):
                current_dt += timedelta(seconds=15)
                gps_points.append({
                    "timestamp": current_dt.astimezone(timezone.utc),
                    "motorista_id": motorista["_id"],
                    "jornada_id": jornada_id,
                    "localizacao": {"type": "Point", "coordinates": route_coords[-1]},
                    "distancia_ultima_m": 0.0,
                    "status": "PARADO",
                    "rua": coords_with_streets[-1][1]
                })
            refuel_done = True
            
    # Fim da jornada
    events.append({
        "tipo": "FIM_JORNADA",
        "timestamp": current_dt.astimezone(timezone.utc),
        "km": km_current
    })
    
    jornada = {
        "_id": jornada_id,
        "motorista_id": motorista["_id"],
        "veiculo_id": veiculo_id,
        "data": target_date.isoformat(),
        "status": "FINALIZADA",
        "km_inicial": km_inicial,
        "km_final": km_current,
        "foto_odometro_inicial_url": "https://placehold.co/600x400?text=Odometro+Inicial",
        "foto_odometro_final_url": "https://placehold.co/600x400?text=Odometro+Final",
        "eventos": events,
        "created_at": datetime.now(timezone.utc)
    }
    
    if gps_points:
        await db["historico_gps"].insert_many(gps_points)
    await db["jornadas"].insert_one(jornada)
    
    print(f"  [Jornada] {motorista['nome']} em {target_date.isoformat()} com {len(gps_points)} pontos de telemetria cadastrados.")

async def main():
    print(f"Conectando ao MongoDB em {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()
    
    print("Limpando banco de dados (exceto administradores/gestores)...")
    await db["users"].delete_many({"role": {"$nin": ["ADMIN", "GESTOR"]}})
    await db["jornadas"].delete_many({})
    await db["historico_gps"].delete_many({})
    await db["corridas_uber"].delete_many({})
    await db["corridas_99"].delete_many({})
    await db["veiculos"].delete_many({})
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_senha(senha: str) -> str:
        return pwd_context.hash(senha)
        
    drivers_data = [
        {
            "_id": ObjectId("6a3ff9067110907bfff38f51"),
            "nome": "Carlos Silva",
            "email": "carlos@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "111.111.111-11", "telefone": "27999990001", "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "077 - INTER", "agencia": "1", "conta": "12345-1", "cnpj": "11.111.111/0001-11", "empresa": "Parceiro A LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f52"),
            "nome": "Bruno Souza",
            "email": "bruno@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "222.222.222-22", "telefone": "27999990002", "nivel_id": "N2",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "260 - NUBANK", "agencia": "1", "conta": "12345-2", "cnpj": "22.222.222/0001-22", "empresa": "Parceiro B LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f53"),
            "nome": "Marcos Santos",
            "email": "motorista@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "333.333.333-33", "telefone": "27999990003", "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "341 - ITAU", "agencia": "1", "conta": "12345-3", "cnpj": "33.333.333/0001-33", "empresa": "Parceiro C LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f54"),
            "nome": "Renato Lima",
            "email": "renato@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "444.444.444-44", "telefone": "27999990004", "nivel_id": "N3",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "033 - SANTANDER", "agencia": "1", "conta": "12345-4", "cnpj": "44.444.444/0001-44", "empresa": "Parceiro D LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f55"),
            "nome": "Julio Cesar",
            "email": "julio@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "555.555.555-55", "telefone": "27999990005", "nivel_id": "N2",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "001 - BANCO DO BRASIL", "agencia": "1", "conta": "12345-5", "cnpj": "55.555.555/0001-55", "empresa": "Parceiro E LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
        {
            "_id": ObjectId("6a3ff9067110907bfff38f56"),
            "nome": "Roberto Alves",
            "email": "roberto@test.com",
            "senha_hash": hash_senha("123456"),
            "pin_hash": hash_senha("1234"),
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "666.666.666-66", "telefone": "27999990006", "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "104 - CAIXA", "agencia": "1", "conta": "12345-6", "cnpj": "66.666.666/0001-66", "empresa": "Parceiro F LTDA"},
                "limiar_inatividade_minutos": 15
            }
        }
    ]
    
    await db["users"].insert_many(drivers_data)
    print("6 Motoristas cadastrados no banco de dados!")
    
    veiculos_data = [
        {"_id": "AAA-1A11", "id_placa": "AAA-1A11", "marca_modelo": "Hyundai HB20", "ano_modelo": "2023", "cor": "Prata", "situacao": "RODANDO", "km_atual": 20120.0},
        {"_id": "BBB-2B22", "id_placa": "BBB-2B22", "marca_modelo": "Chevrolet Onix", "ano_modelo": "2022", "cor": "Preto", "situacao": "RODANDO", "km_atual": 15300.0},
        {"_id": "CCC-3C33", "id_placa": "CCC-3C33", "marca_modelo": "Fiat Cronos", "ano_modelo": "2023", "cor": "Branco", "situacao": "RODANDO", "km_atual": 9045.0},
        {"_id": "DDD-4D44", "id_placa": "DDD-4D44", "marca_modelo": "Volkswagen Polo", "ano_modelo": "2023", "cor": "Cinza", "situacao": "RODANDO", "km_atual": 12000.0},
        {"_id": "EEE-5E55", "id_placa": "EEE-5E55", "marca_modelo": "Renault Sandero", "ano_modelo": "2022", "cor": "Vermelho", "situacao": "RODANDO", "km_atual": 18000.0}
    ]
    await db["veiculos"].insert_many(veiculos_data)
    print("5 Veículos cadastrados!")
    
    async with httpx.AsyncClient() as http_client:
        await prefetch_all_routes(http_client)
        
    sequences = {
        "Carlos Silva": ["laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "centro_vitoria", "praia_do_canto", "ufes", "jardim_camburi", "carapina", "laranjeiras"],
        "Bruno Souza": ["rodoviaria", "centro_vitoria", "praia_do_canto", "ufes", "jardim_camburi", "carapina", "laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria"],
        "Marcos Santos": ["jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "jardim_camburi"],
        "Renato Lima": ["ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "ufes"],
        "Julio Cesar": ["carapina", "laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria", "rodoviaria", "centro_vitoria", "praia_do_canto", "ufes", "jardim_camburi", "carapina"],
        "Roberto Alves": ["centro_vitoria", "rodoviaria", "centro_vitoria", "praia_do_canto", "ufes", "jardim_camburi", "carapina", "laranjeiras", "carapina", "jardim_camburi", "ufes", "praia_do_canto", "centro_vitoria"]
    }
    
    # 6 drivers configurations (overlapping and midnight shifts)
    shifts = [
        # Manhã: 07:00 as 16:00
        {"driver_idx": 0, "plate": "AAA-1A11", "start": "07:00"},
        {"driver_idx": 1, "plate": "BBB-2B22", "start": "07:00"},
        {"driver_idx": 2, "plate": "CCC-3C33", "start": "07:00"},
        # Tarde: 15:00 as 00:00
        {"driver_idx": 3, "plate": "AAA-1A11", "start": "15:00"},
        {"driver_idx": 4, "plate": "BBB-2B22", "start": "15:00"},
        # Madrugada: 23:00 as 07:00
        {"driver_idx": 5, "plate": "CCC-3C33", "start": "23:00"},
    ]
    
    local_tz = pytz.timezone("America/Sao_Paulo")
    today = datetime.now(local_tz).date()
    
    print("Gerando histórico para os últimos 5 dias...")
    for day_offset in range(4, -1, -1):
        target_date = today - timedelta(days=day_offset)
        print(f"\n--- Processando Dia: {target_date.isoformat()} ---")
        
        for config in shifts:
            motorista = drivers_data[config["driver_idx"]]
            name = motorista["nome"]
            seq = sequences[name]
            plate = config["plate"]
            start_time = config["start"]
            
            await generate_journey_for_sequence(
                db, motorista, plate, target_date, start_time, seq
            )
            
    print("\n--- MOCK COMPLETO E ROTA COM RUAS SEEDADOS COM SUCESSO ---")

if __name__ == "__main__":
    asyncio.run(main())
