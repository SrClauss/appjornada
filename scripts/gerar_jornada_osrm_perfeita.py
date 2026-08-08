import asyncio
from datetime import datetime, timezone, timedelta
import json
import urllib.request
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

try:
    from app.core.config import settings
    MONGO_URL = settings.MONGO_URL
except Exception:
    MONGO_URL = "mongodb://admin:secret123@mongo:27017/appjornada?authSource=admin"

OSRM_URL = "http://osrm:5000/route/v1/driving"

import os
json_locations = [
    "/app/corridas_sequenciais.json",
    "/app/teste_deslocamento/corridas_sequenciais.json",
    "/home/claus/src/app_jornada/teste_deslocamento/corridas_sequenciais.json",
    "teste_deslocamento/corridas_sequenciais.json"
]

dataset = None
for loc in json_locations:
    if os.path.exists(loc):
        with open(loc, "r", encoding="utf-8") as f:
            dataset = json.load(f)
            print(f"Carregado JSON de {loc}")
            break

if not dataset:
    raise FileNotFoundError("Não foi possível encontrar corridas_sequenciais.json")

segmentos = dataset["segmentos"]

print(f"Carregados {len(segmentos)} segmentos de jornada.")

def get_osrm_full_geometry(orig, dest):
    """ Busca no OSRM a rota completa via asfalto (todos os pontos da malha viária) """
    url = f"{OSRM_URL}/{orig['lon']},{orig['lat']};{dest['lon']},{dest['lat']}?geometries=geojson&overview=full"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data["code"] == "Ok" and len(data["routes"]) > 0:
                    coords = data["routes"][0]["geometry"]["coordinates"] # [[lon, lat], ...]
                    return coords
    except Exception as e:
        print(f"Erro ao buscar OSRM ({orig['bairro']} ➔ {dest['bairro']}):", e)
    
    # Fallback simples caso OSRM falhe
    return [[orig['lon'], orig['lat']], [dest['lon'], dest['lat']]]

all_gps_docs = []

# ID fixo da Jornada de Teste do Clausemberg
JORNADA_ID = "Clausemberg Rodrigues de Olvierira-TEST-1234-07082026150119"
MOTORISTA_ID = ObjectId("6a40670ec7008f9c4eeb44e2")

# Relógio contínuo iniciando no dia 07/08/2026 às 06:10:00
running_time = datetime(2026, 8, 7, 6, 10, 0, tzinfo=timezone.utc)

# Processar cada segmento (uma a uma, sem pressa, com log detalhado)
for idx, seg in enumerate(segmentos, start=1):
    tipo = seg["tipo"]
    titulo = seg["titulo"]
    orig = seg["origem"]
    dest = seg["destino"]
    
    # Calcular duração em segundos a partir do texto formatado ou min/sec
    dur_str = seg.get("duracao", "5 min 0 s")
    # Tentar extrair minutos e segundos da string
    mins, secs = 5, 0
    try:
        parts = dur_str.split()
        if "min" in parts:
            mins = int(parts[parts.index("min") - 1])
        if "s" in parts:
            secs = int(parts[parts.index("s") - 1])
    except Exception:
        pass
        
    duracao_total_sec = (mins * 60) + secs
    if duracao_total_sec <= 0:
        duracao_total_sec = 60.0

    dt_inicio = running_time
    dt_fim = dt_inicio + timedelta(seconds=duracao_total_sec)
    running_time = dt_fim # Avança o relógio contínuo para o próximo segmento!

    # Buscar a malha de asfalto completa do OSRM
    coords = get_osrm_full_geometry(orig, dest)
    num_pontos = len(coords)
    
    print(f"[{idx}/{len(segmentos)}] {titulo} ({seg['horario_inicio']} ➔ {seg['horario_fim']}) -> {num_pontos} vértices de asfalto OSRM")

    # Calcular distancias acumuladas entre os pontos da rota
    dist_acumulada = [0.0]
    total_dist = 0.0
    for i in range(len(coords) - 1):
        d_lon = coords[i+1][0] - coords[i][0]
        d_lat = coords[i+1][1] - coords[i][1]
        # Distancia aproximada em graus geográficos
        d = (d_lon**2 + d_lat**2)**0.5
        total_dist += d
        dist_acumulada.append(total_dist)

    # Gerar ponto GPS para cada vértice da rota OSRM!
    for i, c in enumerate(coords):
        frac = dist_acumulada[i] / total_dist if total_dist > 0 else (i / (num_pontos - 1) if num_pontos > 1 else 0)
        
        # Timestamp exato proporcional à posição no trajeto
        sec_offset = frac * duracao_total_sec
        pt_dt = dt_inicio + timedelta(seconds=sec_offset)
        
        lon, lat = c[0], c[1]
        
        status_gps = "CONDUZINDO" if tipo == "CORRIDA" else "DESLOCAMENTO"
        
        doc = {
            "jornada_id": JORNADA_ID,
            "motorista_id": MOTORISTA_ID,
            "timestamp": pt_dt,
            "localizacao": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "lat": lat,
            "lon": lon,
            "status": status_gps,
            "distancia_ultima_m": 50.0 if status_gps == "CONDUZINDO" else 30.0,
            "detalhes": f"{tipo} | OSRM Asfalto | Vertice {i+1}/{num_pontos}"
        }
        all_gps_docs.append(doc)

print(f"\n==========================================")
print(f"Total de pontos de GPS gerados com asfalto OSRM: {len(all_gps_docs)}")
print(f"==========================================\n")

async def salvar_no_banco():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_database()
    
    # 1. Limpar telemetria antiga da jornada
    del_res = await db["historico_gps"].delete_many({"jornada_id": JORNADA_ID})
    print(f"Telemetria antiga removida: {del_res.deleted_count} documentos.")
    
    # 2. Inserir os novos pontos OSRM perfeitos
    if all_gps_docs:
        ins_res = await db["historico_gps"].insert_many(all_gps_docs)
        print(f"Sucesso! Inseridos {len(ins_res.inserted_ids)} pontos de GPS idênticos ao OSRM no MongoDB.")

asyncio.run(salvar_no_banco())
