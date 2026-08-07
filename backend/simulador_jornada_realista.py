import asyncio
import json
import random
import urllib.request
import httpx
from bson import ObjectId
from datetime import datetime, timedelta, timezone
from app.db.database import get_db

# Apenas Pontos em São Mateus
POIS = [
    {"id": 1, "nome": "Igreja Velha", "categoria": "História", "lat": -18.7214, "lon": -39.8551},
    {"id": 2, "nome": "Catedral de São Mateus", "categoria": "Religioso", "lat": -18.7205, "lon": -39.8543},
    {"id": 3, "nome": "Sítio Histórico", "categoria": "Cultura", "lat": -18.7221, "lon": -39.8562},
    {"id": 4, "nome": "Museu Municipal", "categoria": "Museu", "lat": -18.7230, "lon": -39.8545},
    {"id": 5, "nome": "Praça Mesquita Neto", "categoria": "Lazer", "lat": -18.7185, "lon": -39.8571},
    {"id": 6, "nome": "Igreja São Benedito", "categoria": "Religioso", "lat": -18.7202, "lon": -39.8580},
    {"id": 7, "nome": "Mercado Municipal", "categoria": "Comércio", "lat": -18.7191, "lon": -39.8555},
    {"id": 8, "nome": "Praça São Benedito", "categoria": "Lazer", "lat": -18.7211, "lon": -39.8585},
    {"id": 9, "nome": "Shopping São Mateus", "categoria": "Comércio", "lat": -18.7150, "lon": -39.8500},
    {"id": 10, "nome": "Rio Cricaré", "categoria": "Natureza", "lat": -18.7240, "lon": -39.8590},
    {"id": 17, "nome": "Espaço Beira Rio", "categoria": "Lazer", "lat": -18.7200, "lon": -39.8560},
    {"id": 18, "nome": "Hospital Roberto Silvares", "categoria": "Saúde", "lat": -18.7061, "lon": -39.8601},
    {"id": 19, "nome": "Terminal Rodoviário", "categoria": "Transporte", "lat": -18.7170, "lon": -39.8588},
    {"id": 20, "nome": "Fares (Supermercado)", "categoria": "Comércio", "lat": -18.7188, "lon": -39.8530},
    {"id": 21, "nome": "Praça do Avião", "categoria": "Lazer", "lat": -18.7118, "lon": -39.8475},
]

BASE_OPERACAO = {"nome": "Base de Operações - Rua Laura Crespo Maia", "lat": -18.71439200, "lon": -39.82804900}
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"

async def get_osrm_route(p1: dict, p2: dict):
    coords_str = f"{p1['lon']},{p1['lat']};{p2['lon']},{p2['lat']}"
    url = f"{OSRM_URL}/{coords_str}?overview=full&geometries=geojson"
    
    for attempt in range(5):
        try:
            await asyncio.sleep(0.05)
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        coords = route["geometry"]["coordinates"]
                        if len(coords) >= 2:
                            return {
                                "distance_m": route.get("distance", 5000.0),
                                "duration_s": route.get("duration", 600.0),
                                "coordinates": coords
                            }
        except Exception:
            await asyncio.sleep(0.2)
            
    try:
        req = urllib.request.urlopen(url, timeout=10)
        data = json.loads(req.read().decode())
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            coords = route["geometry"]["coordinates"]
            if len(coords) >= 2:
                return {
                    "distance_m": route.get("distance", 5000.0),
                    "duration_s": route.get("duration", 600.0),
                    "coordinates": coords
                }
    except Exception as e:
        print(f"❌ Falha OSRM entre {p1['nome']} e {p2['nome']}: {e}")

    return {
        "distance_m": 5000.0,
        "duration_s": 600.0,
        "coordinates": [[p1["lon"], p1["lat"]], [p2["lon"], p2["lat"]]]
    }

async def rodar_simulacao_jornada():
    db = get_db()
    jornada_id = "Clausemberg Rodrigues de Olvierira-TEST-1234-07082026150119"
    motorista_id = "6a40670ec7008f9c4eeb44e2"

    jornada = await db["jornadas"].find_one({"_id": jornada_id})
    if not jornada:
        print(f"❌ Jornada {jornada_id} não encontrada!")
        return

    # Limpa histórico antigo de GPS
    await db["historico_gps"].delete_many({"jornada_id": jornada_id})

    # UTC-3 para São Mateus-ES
    tz_br = timezone(timedelta(hours=-3))
    
    # Início hoje (07/08/2026) às 05:00 local (08:00 UTC)
    inicio_jornada_local = datetime(2026, 8, 7, 5, 0, 0, tzinfo=tz_br)
    fim_jornada_local = datetime(2026, 8, 7, 16, 0, 0, tzinfo=tz_br)
    
    tempo_atual = inicio_jornada_local.astimezone(timezone.utc)
    fim_jornada = fim_jornada_local.astimezone(timezone.utc)

    print(f"🚀 Gerando Rota (05:00 as 16:00) apenas em São Mateus...")

    gps_points = []
    pausas = []
    abastecimentos = []
    km_acumulado = 1000.0

    loc_base_pydantic = {"lat": BASE_OPERACAO["lat"], "lon": BASE_OPERACAO["lon"]}

    # 1. PRIMEIRA PAUSA NA BASE DE OPERAÇÕES (Início da Jornada)
    pausas.append({
        "id": f"pausa-inicio-{int(tempo_atual.timestamp())}",
        "tipo": "PAUSA_MOTORISTA",
        "inicio": tempo_atual.astimezone(tz_br).strftime("%H:%M:%S"),
        "fim": (tempo_atual + timedelta(minutes=15)).astimezone(tz_br).strftime("%H:%M:%S"),
        "duracao_segundos": 900,
        "localizacao_inicio": loc_base_pydantic,
        "localizacao_fim": loc_base_pydantic,
    })
    gps_points.append({
        "jornada_id": jornada_id,
        "motorista_id": ObjectId(motorista_id),
        "timestamp": tempo_atual,
        "localizacao": {"type": "Point", "coordinates": [BASE_OPERACAO["lon"], BASE_OPERACAO["lat"]]},
        "distancia_ultima_m": 0.0,
        "status": "PARADO",
        "rua": "Base de Operações São Mateus",
        "contador_mesclados": 1,
    })
    tempo_atual += timedelta(minutes=15)

    ponto_atual = BASE_OPERACAO
    almoco_realizado = False
    abastecimento_realizado = False
    
    # 2. Ciclos de viagens até 15:40 (para dar tempo de voltar pra base)
    while tempo_atual < (fim_jornada - timedelta(minutes=20)):
        hora_local = tempo_atual.astimezone(tz_br).hour
        
        # Abastecimento (10:xx)
        if hora_local == 10 and not abastecimento_realizado:
            abastecimento_realizado = True
            posto = {"nome": "Posto Ale (Centro)", "lat": -18.7180, "lon": -39.8550}
            route_posto = await get_osrm_route(ponto_atual, posto)
            # Vai pro posto
            for coord in route_posto["coordinates"]:
                step_dur = max(1, int(route_posto["duration_s"] / max(len(route_posto["coordinates"]), 1)))
                tempo_atual += timedelta(seconds=step_dur)
                gps_points.append({
                    "jornada_id": jornada_id, "motorista_id": ObjectId(motorista_id), "timestamp": tempo_atual,
                    "localizacao": {"type": "Point", "coordinates": coord}, "distancia_ultima_m": route_posto["distance_m"] / max(len(route_posto["coordinates"]), 1),
                    "status": "CONDUZINDO", "rua": f"Deslocamento: Posto", "contador_mesclados": 1
                })
            km_acumulado += route_posto["distance_m"] / 1000.0
            ponto_atual = posto
            # Abastece
            abastecimentos.append({
                "id": f"abast-{int(tempo_atual.timestamp())}",
                "hora_inicio": tempo_atual.astimezone(tz_br).strftime("%H:%M:%S"),
                "hora_fim": (tempo_atual + timedelta(minutes=15)).astimezone(tz_br).strftime("%H:%M:%S"),
                "km": round(km_acumulado, 1),
                "valor_gasolina": 180.00,
                "foto_comprovante_url": "https://storage.arkana.fun/jornadas/comprovantes/abastecimento_teste.jpg",
            })
            tempo_atual += timedelta(minutes=15)
            continue
            
        # Almoço (12:xx)
        if hora_local == 12 and not almoco_realizado:
            almoco_realizado = True
            restaurante = {"nome": "Restaurante Central", "lat": -18.7200, "lon": -39.8540}
            route_rest = await get_osrm_route(ponto_atual, restaurante)
            for coord in route_rest["coordinates"]:
                step_dur = max(1, int(route_rest["duration_s"] / max(len(route_rest["coordinates"]), 1)))
                tempo_atual += timedelta(seconds=step_dur)
                gps_points.append({
                    "jornada_id": jornada_id, "motorista_id": ObjectId(motorista_id), "timestamp": tempo_atual,
                    "localizacao": {"type": "Point", "coordinates": coord}, "distancia_ultima_m": route_rest["distance_m"] / max(len(route_rest["coordinates"]), 1),
                    "status": "CONDUZINDO", "rua": f"Deslocamento: Restaurante", "contador_mesclados": 1
                })
            km_acumulado += route_rest["distance_m"] / 1000.0
            ponto_atual = restaurante
            
            pausas.append({
                "id": f"pausa-almoco-{int(tempo_atual.timestamp())}",
                "tipo": "ALMOCO",
                "inicio": tempo_atual.astimezone(tz_br).strftime("%H:%M:%S"),
                "fim": (tempo_atual + timedelta(hours=1)).astimezone(tz_br).strftime("%H:%M:%S"),
                "duracao_segundos": 3600,
                "localizacao_inicio": {"lat": ponto_atual["lat"], "lon": ponto_atual["lon"]},
                "localizacao_fim": {"lat": ponto_atual["lat"], "lon": ponto_atual["lon"]},
            })
            tempo_atual += timedelta(hours=1)
            continue

        # Corrida Aleatória
        # 2a. Deslocamento até passageiro
        local_passageiro = random.choice([p for p in POIS if p["id"] != ponto_atual.get("id", -1)])
        route_busca = await get_osrm_route(ponto_atual, local_passageiro)
        for coord in route_busca["coordinates"]:
            step_dur = max(1, int(route_busca["duration_s"] / max(len(route_busca["coordinates"]), 1)))
            tempo_atual += timedelta(seconds=step_dur)
            gps_points.append({
                "jornada_id": jornada_id, "motorista_id": ObjectId(motorista_id), "timestamp": tempo_atual,
                "localizacao": {"type": "Point", "coordinates": coord}, "distancia_ultima_m": route_busca["distance_m"] / max(len(route_busca["coordinates"]), 1),
                "status": "CONDUZINDO", "rua": f"Buscando passageiro: {local_passageiro['nome']}", "contador_mesclados": 1
            })
        km_acumulado += route_busca["distance_m"] / 1000.0
        ponto_atual = local_passageiro
        
        # Simula espera passageiro embarcar
        tempo_atual += timedelta(minutes=1)
        
        # 2b. Viagem com passageiro
        destino_corrida = random.choice([p for p in POIS if p["id"] != ponto_atual["id"]])
        route_viagem = await get_osrm_route(ponto_atual, destino_corrida)
        for coord in route_viagem["coordinates"]:
            step_dur = max(1, int(route_viagem["duration_s"] / max(len(route_viagem["coordinates"]), 1)))
            tempo_atual += timedelta(seconds=step_dur)
            gps_points.append({
                "jornada_id": jornada_id, "motorista_id": ObjectId(motorista_id), "timestamp": tempo_atual,
                "localizacao": {"type": "Point", "coordinates": coord}, "distancia_ultima_m": route_viagem["distance_m"] / max(len(route_viagem["coordinates"]), 1),
                "status": "CONDUZINDO", "rua": f"Viagem p/: {destino_corrida['nome']}", "contador_mesclados": 1
            })
        km_acumulado += route_viagem["distance_m"] / 1000.0
        ponto_atual = destino_corrida
        
        # Simula desembarque
        tempo_atual += timedelta(minutes=1)

    # 3. Retorno para a Base de Operações (Ajustando tempo para terminar as 16:00 cravado)
    print(f"🏠 Retornando para a Base de Operações às 16:00...")
    route_base = await get_osrm_route(ponto_atual, BASE_OPERACAO)
    
    # Distribui os pontos no tempo restante até 16:00
    segundos_restantes = max(10, (fim_jornada - tempo_atual).total_seconds())
    
    for coord in route_base["coordinates"]:
        step_dur = max(1, int(segundos_restantes / max(len(route_base["coordinates"]), 1)))
        tempo_atual += timedelta(seconds=step_dur)
        # Garantir que não passe das 16:00 cravado
        if tempo_atual > fim_jornada:
            tempo_atual = fim_jornada
            
        gps_points.append({
            "jornada_id": jornada_id,
            "motorista_id": ObjectId(motorista_id),
            "timestamp": tempo_atual,
            "localizacao": {"type": "Point", "coordinates": coord},
            "distancia_ultima_m": route_base["distance_m"] / max(len(route_base["coordinates"]), 1),
            "status": "CONDUZINDO",
            "rua": "Retorno Base - Fim de Expediente",
            "contador_mesclados": 1,
        })
    km_acumulado += route_base["distance_m"] / 1000.0
    
    # Força tempo exato 16:00
    tempo_atual = fim_jornada

    # 4. ÚLTIMA PAUSA NA BASE DE OPERAÇÕES (Fim da Jornada)
    pausas.append({
        "id": f"pausa-final-{int(tempo_atual.timestamp())}",
        "tipo": "PAUSA_MOTORISTA",
        "inicio": tempo_atual.astimezone(tz_br).strftime("%H:%M:%S"),
        "fim": tempo_atual.astimezone(tz_br).strftime("%H:%M:%S"),
        "duracao_segundos": 0,
        "localizacao_inicio": loc_base_pydantic,
        "localizacao_fim": loc_base_pydantic,
    })
    gps_points.append({
        "jornada_id": jornada_id,
        "motorista_id": ObjectId(motorista_id),
        "timestamp": tempo_atual,
        "localizacao": {"type": "Point", "coordinates": [BASE_OPERACAO["lon"], BASE_OPERACAO["lat"]]},
        "distancia_ultima_m": 0.0,
        "status": "PARADO",
        "rua": "Base de Operações São Mateus",
        "contador_mesclados": 1,
    })

    # Inserção em lotes
    print(f"📦 Salvando {len(gps_points)} pontos viários OSRM no banco...")
    batch_size = 100
    for i in range(0, len(gps_points), batch_size):
        await db["historico_gps"].insert_many(gps_points[i:i+batch_size])

    km_rodados = round(km_acumulado - 1000.0, 1)

    # Atualiza a Jornada com formato Pydantic perfeitamente validado
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {
            "$set": {
                "horario.inicio": inicio_jornada_local.strftime("%H:%M:%S"),
                "horario.fim": fim_jornada_local.strftime("%H:%M:%S"),
                "data": inicio_jornada_local.strftime("%Y-%m-%d"),
                "abastecimentos": abastecimentos,
                "pausas": pausas,
                "km": {
                    "inicial": 1000.0,
                    "final": round(km_acumulado, 1),
                    "rodados": km_rodados,
                    "atual": round(km_acumulado, 1),
                    "morta": 1.0,
                    "inicial_contestado": False,
                    "final_contestado": False
                },
                "localizacao_atual": loc_base_pydantic,
                "ultima_atividade_timestamp": tempo_atual,
                "status": "ABERTA"
            }
        }
    )

    print("\n" + "="*60)
    print("✅ JORNADA COMPLETAMENTE REFEITA - SÓ SÃO MATEUS (05h as 16h)!")
    print(f"📍 Total Coordenadas: {len(gps_points)} pontos")
    print(f"🚗 KM Rodados: {km_rodados} km")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(rodar_simulacao_jornada())
