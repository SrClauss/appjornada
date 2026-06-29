import os
import asyncio
from datetime import datetime, date, time, timedelta, timezone
from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import pytz

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/appjornada")

async def main():
    print(f"Conectando ao MongoDB em {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()

    # 1. Limpar banco de dados completely
    print("Limpando dados anteriores...")
    await db["users"].drop()
    await db["jornadas"].drop()
    await db["historico_gps"].drop()
    await db["corridas_uber"].drop()
    await db["corridas_99"].drop()
    await db["veiculos"].drop()

    # 2. Recriar índices
    from pymongo import ASCENDING, GEOSPHERE
    print("Criando índices...")
    await db["users"].create_index("email", unique=True)
    await db["jornadas"].create_index([("motorista_id", ASCENDING), ("data", ASCENDING)])
    await db["jornadas"].create_index("status")
    await db["historico_gps"].create_index([("motorista_id", ASCENDING), ("timestamp", ASCENDING)])
    await db["historico_gps"].create_index([("localizacao", GEOSPHERE)])
    await db["corridas_uber"].create_index("trip_id", unique=True)
    await db["corridas_99"].create_index("trip_id", unique=True)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_senha(senha: str) -> str:
        return pwd_context.hash(senha)

    # 4. Criar os motoristas e administradores
    drivers_data = [
        {
            "_id": ObjectId("6a403ff7734db0687aa06ee1"),
            "nome": "Admin",
            "email": "admin@admin.com",
            "senha_hash": "$2b$12$mJdkPTweFJfPoVmNPiC56eG90uekBKrq/2ngjQm/hRc7JtaDVBVHS",
            "pin_hash": None,
            "role": "ADMIN",
            "situacao": "Ativo",
            "perfil_motorista": None
        },
        {
            "_id": ObjectId("6a40670ec7008f9c4eeb44e2"),
            "nome": "Clausemberg Rodrigues de Olvierira",
            "email": "clausemberg@yahoo.com.br",
            "senha_hash": "$2b$12$2OWrXjry1kOAOidIHbrkyuqCukhwTuUZv/JHusciFjoJ8V5WapfIO",
            "pin_hash": "$2b$12$dgHe73q3RrPBNxYz/NKnuuyFIvu92FyMwGCdIfoY571.WfENo9/Le",
            "role": "MOTORISTA",
            "situacao": "Ativo",
            "perfil_motorista": {
                "cpf": "777.777.777-77", "telefone": "27999990007", "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "077 - INTER", "agencia": "1", "conta": "12345-7", "cnpj": "77.777.777/0001-77", "empresa": "Parceiro Clausemberg LTDA"},
                "limiar_inatividade_minutos": 15
            }
        },
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
                "cpf": "555.555.555-55", "telefone": "27999990005", "nivel_id": "N1",
                "cnh": {"vencimento": "2030-01-01", "imagem_url": None},
                "dados_bancarios": {"banco": "237 - BRADESCO", "agencia": "1", "conta": "12345-5", "cnpj": "55.555.555/0001-55", "empresa": "Parceiro E LTDA"},
                "limiar_inatividade_minutos": 15
            }
        }
    ]
    await db["users"].insert_many(drivers_data)
    print("Motoristas e Admins inseridos com sucesso!")

    # 5. Criar veículos
    veiculos_data = [
        {"_id": "AAA-1A11", "id_placa": "AAA-1A11", "marca_modelo": "Hyundai HB20", "ano_modelo": "2023", "cor": "Prata", "situacao": "RODANDO", "km_atual": 20120.0},
        {"_id": "BBB-2B22", "id_placa": "BBB-2B22", "marca_modelo": "Chevrolet Onix", "ano_modelo": "2022", "cor": "Preto", "situacao": "RODANDO", "km_atual": 15300.0},
        {"_id": "CCC-3C33", "id_placa": "CCC-3C33", "marca_modelo": "Fiat Cronos", "ano_modelo": "2023", "cor": "Branco", "situacao": "RODANDO", "km_atual": 9045.0},
        {"_id": "DDD-4D44", "id_placa": "DDD-4D44", "marca_modelo": "Toyota Yaris", "ano_modelo": "2023", "cor": "Cinza", "situacao": "RODANDO", "km_atual": 43550.0},
        {"_id": "EEE-5E55", "id_placa": "EEE-5E55", "marca_modelo": "Renault Logan", "ano_modelo": "2021", "cor": "Branco", "situacao": "RODANDO", "km_atual": 27250.0}
    ]
    await db["veiculos"].insert_many(veiculos_data)
    print("5 Veículos inseridos!")

    # 6. Coordenadas base
    lon_carapina, lat_carapina = -40.2694, -20.2446
    lon_rodoviaria, lat_rodoviaria = -40.3444, -20.3204
    lon_ufes, lat_ufes = -40.3015, -20.2762
    lon_praia_canto, lat_praia_canto = -40.2933, -20.3050

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
        print(f"OSRM falhou para {from_lon},{from_lat} -> {to_lon},{to_lat}. Usando fallback linear.")
        num_points = 50
        coords = []
        for i in range(num_points):
            t = i / (num_points - 1)
            lon = from_lon + t * (to_lon - from_lon)
            lat = from_lat + t * (to_lat - from_lat)
            coords.append([lon, lat])
        return coords

    routes = {}
    async with httpx.AsyncClient() as http_client:
        routes["r1_go"] = await get_route(http_client, lon_carapina, lat_carapina, lon_rodoviaria, lat_rodoviaria)
        routes["r1_back"] = await get_route(http_client, lon_rodoviaria, lat_rodoviaria, lon_carapina, lat_carapina)
        routes["r2_go"] = await get_route(http_client, lon_carapina, lat_carapina, lon_ufes, lat_ufes)
        routes["r2_back"] = await get_route(http_client, lon_ufes, lat_ufes, lon_carapina, lat_carapina)
        routes["r3_go"] = await get_route(http_client, lon_carapina, lat_carapina, lon_praia_canto, lat_praia_canto)
        routes["r3_back"] = await get_route(http_client, lon_praia_canto, lat_praia_canto, lon_carapina, lat_carapina)

    local_tz = pytz.timezone("America/Sao_Paulo")
    now_local = datetime.now(local_tz)
    today = now_local.date()

    def make_local_dt(day_date, time_obj):
        dt_naive = datetime.combine(day_date, time_obj)
        return local_tz.localize(dt_naive)

    def to_utc(dt_aware):
        return dt_aware.astimezone(timezone.utc)

    def simulate_gps_for_shift(route_go, route_back, start_dt, num_trips, motorista_id, jornada_id, km_base, dist_trip_m, interval_seconds=120):
        # Determine route name based on route_go destination
        last_coord = route_go[-1]
        lon_dest = last_coord[0]
        if abs(lon_dest - (-40.3444)) < 0.01:
            route_name = "r1"
        elif abs(lon_dest - (-40.3015)) < 0.01:
            route_name = "r2"
        else:
            route_name = "r3"

        def get_street_name_for_coord(r_name, going, progress):
            if r_name == "r1":
                streets = [
                    "Rodovia das Paneleiras",
                    "Avenida Fernando Ferrari",
                    "Avenida Elias Miguel",
                    "Avenida Getúlio Vargas",
                    "Avenida Alexandre Buaiz"
                ]
            elif r_name == "r2":
                streets = [
                    "Rodovia das Paneleiras",
                    "Avenida Fernando Ferrari",
                    "Avenida Fernando Ferrari",
                    "Avenida Fernando Ferrari",
                    "Avenida Fernando Ferrari"
                ]
            else:
                streets = [
                    "Rodovia das Paneleiras",
                    "Avenida Fernando Ferrari",
                    "Avenida Nossa Senhora da Penha",
                    "Rua Joaquim Lírio",
                    "Avenida Saturnino de Brito"
                ]
            if not going:
                streets = list(reversed(streets))
            idx = min(int(progress * len(streets)), len(streets) - 1)
            return streets[idx]

        gps_points = []
        current_dt = start_dt
        current_odometer = km_base
        
        # Each trip takes 25 minutes of driving.
        trip_duration_seconds = 25 * 60
        points_per_trip = trip_duration_seconds // interval_seconds
        if points_per_trip < 2:
            points_per_trip = 2
            
        for trip_idx in range(num_trips):
            is_going = (trip_idx % 2 == 0)
            route = route_go if is_going else route_back
            
            # 1. Generate driving points
            for p_idx in range(points_per_trip):
                t = p_idx / (points_per_trip - 1)
                coord_idx = int(t * (len(route) - 1))
                lon, lat = route[coord_idx]
                
                # Odometer increment
                dist_step = dist_trip_m / points_per_trip
                current_odometer += dist_step / 1000.0
                
                gps_points.append({
                    "timestamp": to_utc(current_dt),
                    "motorista_id": motorista_id,
                    "jornada_id": jornada_id,
                    "localizacao": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "distancia_ultima_m": dist_step,
                    "status": "CONDUZINDO",
                    "rua": get_street_name_for_coord(route_name, is_going, t)
                })
                current_dt += timedelta(seconds=interval_seconds)
                
            # 2. Add break
            last_lon, last_lat = route[-1]
            if trip_idx == (num_trips // 2) - 1:
                # 60 mins lunch break
                lunch_seconds = 60 * 60
                for _ in range(lunch_seconds // interval_seconds):
                    gps_points.append({
                        "timestamp": to_utc(current_dt),
                        "motorista_id": motorista_id,
                        "jornada_id": jornada_id,
                        "localizacao": {
                            "type": "Point",
                            "coordinates": [last_lon, last_lat]
                        },
                        "distancia_ultima_m": 0.0,
                        "status": "PARADO",
                        "rua": get_street_name_for_coord(route_name, is_going, 1.0)
                    })
                    current_dt += timedelta(seconds=interval_seconds)
            elif trip_idx < num_trips - 1:
                # 10 mins break
                break_seconds = 10 * 60
                for _ in range(break_seconds // interval_seconds):
                    gps_points.append({
                        "timestamp": to_utc(current_dt),
                        "motorista_id": motorista_id,
                        "jornada_id": jornada_id,
                        "localizacao": {
                            "type": "Point",
                            "coordinates": [last_lon, last_lat]
                        },
                        "distancia_ultima_m": 0.0,
                        "status": "PARADO",
                        "rua": get_street_name_for_coord(route_name, is_going, 1.0)
                    })
                    current_dt += timedelta(seconds=interval_seconds)
                    
        return gps_points, current_odometer, current_dt

    configs = [
        {
            "user_id": ObjectId("6a40670ec7008f9c4eeb44e2"),
            "nome": "Clausemberg Rodrigues de Olvierira",
            "email": "clausemberg@yahoo.com.br",
            "placa": "AAA-1A11",
            "start_time": time(7, 30, 0),
            "route_go": routes["r1_go"],
            "route_back": routes["r1_back"],
            "trips_per_day": 12,
            "dist_trip_m": 15800.0,
            "km_base": 20000.0,
        },
        {
            "user_id": ObjectId("6a3ff9067110907bfff38f51"),
            "nome": "Carlos Silva",
            "email": "carlos@test.com",
            "placa": "AAA-1A11",
            "start_time": time(8, 0, 0),
            "route_go": routes["r1_go"],
            "route_back": routes["r1_back"],
            "trips_per_day": 10,
            "dist_trip_m": 15800.0,
            "km_base": 19000.0,
        },
        {
            "user_id": ObjectId("6a3ff9067110907bfff38f52"),
            "nome": "Bruno Souza",
            "email": "bruno@test.com",
            "placa": "BBB-2B22",
            "start_time": time(8, 30, 0),
            "route_go": routes["r2_go"],
            "route_back": routes["r2_back"],
            "trips_per_day": 14,
            "dist_trip_m": 7700.0,
            "km_base": 14000.0,
        },
        {
            "user_id": ObjectId("6a3ff9067110907bfff38f53"),
            "nome": "Marcos Santos",
            "email": "motorista@test.com",
            "placa": "CCC-3C33",
            "start_time": time(7, 45, 0),
            "route_go": routes["r1_go"],
            "route_back": routes["r1_back"],
            "trips_per_day": 12,
            "dist_trip_m": 15800.0,
            "km_base": 7800.0,
        },
        {
            "user_id": ObjectId("6a3ff9067110907bfff38f54"),
            "nome": "Renato Lima",
            "email": "renato@test.com",
            "placa": "DDD-4D44",
            "start_time": time(9, 0, 0),
            "route_go": routes["r2_go"],
            "route_back": routes["r2_back"],
            "trips_per_day": 16,
            "dist_trip_m": 7700.0,
            "km_base": 42000.0,
        },
        {
            "user_id": ObjectId("6a3ff9067110907bfff38f55"),
            "nome": "Julio Cesar",
            "email": "julio@test.com",
            "placa": "EEE-5E55",
            "start_time": time(8, 15, 0),
            "route_go": routes["r3_go"],
            "route_back": routes["r3_back"],
            "trips_per_day": 10,
            "dist_trip_m": 10500.0,
            "km_base": 26000.0,
        }
    ]

    gps_points_bulk = []
    jornadas_bulk = []

    # 6. Gerar histórico para 25 e 26
    print("Gerando histórico para 25 e 26...")
    for day_offset in [2, 1]:
        day_date = today - timedelta(days=day_offset)
        day_str = day_date.isoformat()

        for cfg in configs:
            if cfg["email"] == "clausemberg@yahoo.com.br":
                continue # Skip Clausemberg!

            jornada_id = f"{cfg['nome']}-{cfg['placa']}-{day_str.replace('-', '')}"
            start_dt = make_local_dt(day_date, cfg["start_time"])
            
            # Start odometer
            km_inicial = cfg["km_base"] + (6 - day_offset) * 150.0
            
            num_trips = cfg["trips_per_day"]
            
            # Generate high-fidelity sequential coordinates
            hist_gps, final_odo, end_dt = simulate_gps_for_shift(
                cfg["route_go"], cfg["route_back"], start_dt, num_trips,
                cfg["user_id"], jornada_id, km_inicial, cfg["dist_trip_m"], interval_seconds=120
            )
            gps_points_bulk.extend(hist_gps)
            
            rodados = round(final_odo - km_inicial, 1)
            total_duration_seconds = int((end_dt - start_dt).total_seconds())
            
            faturamento_uber = round(num_trips * 20.0, 2)
            faturamento_99 = round(num_trips * 12.0, 2)
            faturamento_total = faturamento_uber + faturamento_99

            journey_doc = {
                "_id": jornada_id,
                "data": day_str,
                "motorista_id": cfg["user_id"],
                "veiculo_id": cfg["placa"],
                "status": "ENCERRADA",
                "pin": "1234",
                "km": {
                    "inicial": km_inicial,
                    "final": round(final_odo, 1),
                    "rodados": rodados,
                    "morta": round(rodados * 0.1, 1)
                },
                "faturamento": {
                    "uber": faturamento_uber,
                    "noventa_nove": faturamento_99,
                    "outros": 0.0,
                    "total_dia": faturamento_total
                },
                "vistoria": {
                    "pneus_ok": True, "oleo_ok": True, "agua_ok": True, "farois_ok": True, "limpeza_ok": True, "observacoes": "Checklist matinal OK."
                },
                "localizacao_inicial": {
                    "lat": cfg["route_go"][0][1], "lon": cfg["route_go"][0][0]
                },
                "localizacao_final": {
                    "lat": cfg["route_go"][-1][1], "lon": cfg["route_go"][-1][0]
                },
                "horario": {
                    "inicio": cfg["start_time"].isoformat(),
                    "fim": end_dt.time().isoformat(),
                    "total_horas_segundos": total_duration_seconds
                },
                "pausas": [
                    {
                        "id": f"pausa-almoco-{jornada_id}",
                        "inicio": "12:00:00",
                        "fim": "13:00:00",
                        "tipo": "ALMOCO",
                        "duracao_segundos": 3600,
                        "localizacao_inicio": {"lat": cfg["route_go"][-1][1], "lon": cfg["route_go"][-1][0]},
                        "localizacao_fim": {"lat": cfg["route_go"][-1][1], "lon": cfg["route_go"][-1][0]}
                    }
                ],
                "abastecimentos": [
                    {
                        "id": f"abastecimento-{jornada_id}",
                        "hora_inicio": "10:30:00",
                        "hora_fim": "10:40:00",
                        "duracao_segundos": 600,
                        "km": km_inicial + 35.0,
                        "localizacao": {"lat": cfg["route_go"][0][1], "lon": cfg["route_go"][0][0]},
                        "valor_gasolina": 120.0
                    }
                ],
                "sinistros": [],
                "jornada_diaria_clt": 8.0,
                "jornada_semanal_clt": 44.0,
                "jornada_mensal_clt": 220.0,
                "saldo_horas_dia": round((total_duration_seconds / 3600.0) - 8.0, 2)
            }
            jornadas_bulk.append(journey_doc)

            # Uber rides
            num_uber_runs = num_trips // 2
            for u_idx in range(num_uber_runs):
                c_start = start_dt + timedelta(hours=1 + u_idx)
                c_end = c_start + timedelta(minutes=20)
                trip_uid = f"UBER-{cfg['nome'][:3].upper()}-{day_str.replace('-', '')}-{u_idx}"
                await db["corridas_uber"].insert_one({
                    "trip_id": trip_uid, "id_viagem": trip_uid, "nome_motorista": cfg["nome"], "email_motorista": cfg["email"],
                    "id_colaborador": f"FROTA-{cfg['placa']}", "origem": "Carapina", "destino": "Rodoviária",
                    "inicio": to_utc(c_start), "fim": to_utc(c_end),
                    "duracao_minutos": 20, "programa": "UberX", "tarifa_base": round(faturamento_uber / num_uber_runs, 2),
                    "gorjeta": 0.0, "pedagio": 0.0, "ajuste_tarifa": 0.0, "total_bruto": round(faturamento_uber / num_uber_runs, 2),
                    "total_cobrado": round(faturamento_uber / num_uber_runs, 2), "metodo_pagamento": "Conta digital", "url_fatura": None,
                    "data_importacao": to_utc(now_local)
                })

            # 99 rides
            num_99_runs = num_trips // 2
            for n_idx in range(num_99_runs):
                c_start = start_dt + timedelta(hours=1.5 + n_idx)
                trip_uid = f"99-{cfg['nome'][:3].upper()}-{day_str.replace('-', '')}-{n_idx}"
                await db["corridas_99"].insert_one({
                    "trip_id": trip_uid, "id_corrida": trip_uid, "nome_motorista": cfg["nome"], "centro_custo": f"VEICULO-{cfg['placa']}",
                    "solicitacao": to_utc(c_start), "origem": "Rodoviária", "destino": "Carapina",
                    "distancia_km": round(cfg["dist_trip_m"] / 1000.0, 2), "duracao_minutos": 20,
                    "tarifa_bruta": round((faturamento_99 / num_99_runs) * 1.25, 2), "forma_pagamento": "Cartão Corp",
                    "taxa_intermediacao": round((faturamento_99 / num_99_runs) * 0.25, 2), "descontos": 0.0,
                    "valor_liquido": round(faturamento_99 / num_99_runs, 2), "status": "concluída", "data_importacao": to_utc(now_local)
                })

    # 9. Inserir jornadas e pontos em lote
    print("Salvando no banco de dados...")
    if jornadas_bulk:
        await db["jornadas"].insert_many(jornadas_bulk)
    if gps_points_bulk:
        batch_size = 1000
        for i in range(0, len(gps_points_bulk), batch_size):
            await db["historico_gps"].insert_many(gps_points_bulk[i:i+batch_size])

    print("\n--- MOCK DE ALTA FIDELIDADE GERADO COM SUCESSO ---")
    print(f"Total de Jornadas salvas: {len(jornadas_bulk)}")
    print(f"Total de pontos de GPS salvos: {len(gps_points_bulk)}")
    print("As jornadas de hoje estão ativas e com simulação em tempo real para exibir no painel!")

if __name__ == "__main__":
    asyncio.run(main())
