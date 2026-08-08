import json
import random
from datetime import datetime, timedelta

# Fixar semente para reprodutibilidade
random.seed(42)

LOCAIS = [
    {"lat": -18.7144, "lon": -39.8542, "bairro": "Centro", "rua": "Av. Jones dos Santos Neves"},
    {"lat": -18.7280, "lon": -39.7540, "bairro": "Guriri", "rua": "Av. Oceânica"},
    {"lat": -18.7192, "lon": -39.8510, "bairro": "Sernamby", "rua": "Praça São Benedito"},
    {"lat": -18.7230, "lon": -39.8450, "bairro": "Boa Vista", "rua": "Av. José Tozzi"},
    {"lat": -18.7300, "lon": -39.7500, "bairro": "Guriri Sul", "rua": "Rua 10"},
    {"lat": -18.7050, "lon": -39.8600, "bairro": "Litorâneo", "rua": "Av. Governador Eurico Soares"},
]

def rand_float(min_v, max_v):
    return random.uniform(min_v, max_v)

def rand_int(min_v, max_v):
    return random.randint(min_v, max_v)

def rand_elem(lst):
    return random.choice(lst)

all_rides = []
base_date = datetime(2026, 8, 7, 6, 10, 0) # Começa as 06:10
current_time = base_date

uber_count = 0
n99_count = 0
ride_id = 1

while (uber_count + n99_count) < 100:
    val = round(rand_float(9.00, 48.90), 2)
    km = round(rand_float(1.5, 22.0), 1)
    mins = rand_int(5, 25)
    sec = rand_int(10, 58)
    
    start_t = current_time
    end_t = start_t + timedelta(minutes=mins, seconds=sec)
    
    remaining_uber = 50 - uber_count
    remaining_n99 = 50 - n99_count
    
    if remaining_uber == 0:
        is_uber = False
    elif remaining_n99 == 0:
        is_uber = True
    else:
        is_uber = random.random() > 0.5
        
    loc_o = rand_elem(LOCAIS)
    loc_d = rand_elem([l for l in LOCAIS if l["bairro"] != loc_o["bairro"]])
    
    app_name = "Uber" if is_uber else "99"
    if is_uber:
        uber_count += 1
        cat = 'UberX' if random.random() > 0.4 else ('Comfort' if random.random() > 0.3 else 'Uber Black')
        is_dyn = random.random() < 0.25
        dyn_val = round(rand_float(3.50, 14.20), 2) if is_dyn else None
    else:
        n99_count += 1
        cat = 'Pop' if random.random() > 0.5 else 'Pop Expresso'
        is_dyn = False
        dyn_val = None

    ride_info = {
        "ordem": ride_id,
        "app": app_name,
        "categoria": cat,
        "data": start_t.strftime("%Y-%m-%d"),
        "horario_inicio": start_t.strftime("%H:%M:%S"),
        "horario_fim": end_t.strftime("%H:%M:%S"),
        "timestamp_inicio_iso": start_t.isoformat(),
        "timestamp_fim_iso": end_t.isoformat(),
        "duracao_formatada": f"{mins} min {sec} s",
        "duracao_minutos": mins,
        "duracao_segundos": sec,
        "distancia_km": km,
        "valor_r$": val,
        "preco_dinamico": dyn_val,
        "origem": {
            "bairro": loc_o["bairro"],
            "rua": loc_o["rua"],
            "lat": loc_o["lat"],
            "lon": loc_o["lon"]
        },
        "destino": {
            "bairro": loc_d["bairro"],
            "rua": loc_d["rua"],
            "lat": loc_d["lat"],
            "lon": loc_d["lon"]
        }
    }
    
    all_rides.append(ride_info)
    ride_id += 1
    
    gap_mins = rand_int(2, 6)
    gap_secs = rand_int(0, 59)
    current_time = end_t + timedelta(minutes=gap_mins, seconds=gap_secs)

# Criar lista completa de segmentos alternando CORRIDA e DESLOCAMENTO
segmentos = []
seq_id = 1

for i in range(len(all_rides)):
    r = all_rides[i]
    # 1. Segmento de Corrida
    segmentos.append({
        "seq_id": seq_id,
        "tipo": "CORRIDA",
        "titulo": f"Corrida #{r['ordem']} [{r['app']}]",
        "app": r["app"],
        "categoria": r["categoria"],
        "valor_r$": r["valor_r$"],
        "horario_inicio": r["horario_inicio"],
        "horario_fim": r["horario_fim"],
        "duracao": r["duracao_formatada"],
        "distancia_estimada_km": r["distancia_km"],
        "origem": r["origem"],
        "destino": r["destino"]
    })
    seq_id += 1

    # 2. Segmento de Deslocamento ate a proxima corrida (se houver)
    if i < len(all_rides) - 1:
        r_next = all_rides[i + 1]
        desloc_dur_sec = int((datetime.fromisoformat(r_next["timestamp_inicio_iso"]) - datetime.fromisoformat(r["timestamp_fim_iso"])).total_seconds())
        desloc_mins = desloc_dur_sec // 60
        desloc_secs = desloc_dur_sec % 60

        segmentos.append({
            "seq_id": seq_id,
            "tipo": "DESLOCAMENTO",
            "titulo": f"Deslocamento (Batendo Lata) #{r['ordem']} ➔ #{r_next['ordem']}",
            "app": "Deslocamento",
            "categoria": "Transição de Local",
            "valor_r$": 0.00,
            "horario_inicio": r["horario_fim"],
            "horario_fim": r_next["horario_inicio"],
            "duracao": f"{desloc_mins} min {desloc_secs} s",
            "distancia_estimada_km": "Calculado pelo OSRM",
            "origem": r["destino"],      # Sai de onde a corrida anterior terminou
            "destino": r_next["origem"]   # Vai ate onde a proxima corrida inicia
        })
        seq_id += 1

dataset = {
    "total_corridas": len(all_rides),
    "total_segmentos": len(segmentos),
    "corridas": all_rides,
    "segmentos": segmentos
}

json_path = "/home/claus/src/app_jornada/teste_deslocamento/corridas_sequenciais.json"
js_path = "/home/claus/src/app_jornada/teste_deslocamento/data.js"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2, ensure_ascii=False)

with open(js_path, "w", encoding="utf-8") as f:
    f.write("window.DATASET = " + json.dumps(dataset, indent=2, ensure_ascii=False) + ";")

print(f"Sucesso! Gerados {len(all_rides)} corridas e {len(segmentos)} segmentos em '{json_path}' e '{js_path}'.")
