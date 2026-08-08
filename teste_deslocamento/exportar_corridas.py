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
# Jornada no dia 07/08/2026 das 06:10 em diante
base_date = datetime(2026, 8, 7, 6, 10, 0)
current_time = base_date

uber_count = 0
n99_count = 0
ride_id = 1

# Gerar corridas em sequencia estrita sem sobreposicao
while (uber_count + n99_count) < 100:
    val = round(rand_float(9.00, 48.90), 2)
    km = round(rand_float(1.5, 22.0), 1)
    mins = rand_int(5, 25) # duracao ajustada para caber no mesmo dia
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
    # Garantir que destino e diferente de origem
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
    
    # Intervalo de deslocamento / tempo de espera ate a proxima corrida (2 a 6 minutos)
    gap_mins = rand_int(2, 6)
    gap_secs = rand_int(0, 59)
    current_time = end_t + timedelta(minutes=gap_mins, seconds=gap_secs)

# Salvar em JSON no diretorio teste_deslocamento
output_path = "/home/claus/src/app_jornada/teste_deslocamento/corridas_sequenciais.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_rides, f, indent=2, ensure_ascii=False)

print(f"Sucesso! {len(all_rides)} corridas sequenciais salvas em '{output_path}'.")
