import json
import math
import random
from datetime import datetime, timedelta

# Fix seed for reproducibility
random.seed(42)

# Coordenadas Base para simular
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

# Gerar 100 Corridas não sobrepostas
all_rides = []
current_time = datetime(2026, 8, 7, 6, 10, 0) # Começa as 06:10

uber_count = 0
n99_count = 0

while (uber_count + n99_count) < 100:
    val = round(rand_float(9.00, 48.90), 2)
    km = round(rand_float(1.5, 22.0), 1)
    mins = rand_int(5, 35)
    sec = rand_int(10, 58)
    
    start_t = current_time
    end_t = start_t + timedelta(minutes=mins, seconds=sec)
    
    start_hm = start_t.strftime("%H:%M")
    end_hm = end_t.strftime("%H:%M")
    
    # Decide if Uber or 99
    # If we need exactly 50/50, we can bias it
    remaining_uber = 50 - uber_count
    remaining_n99 = 50 - n99_count
    
    if remaining_uber == 0:
        is_uber = False
    elif remaining_n99 == 0:
        is_uber = True
    else:
        is_uber = random.random() > 0.5
        
    loc_o = rand_elem(LOCAIS)
    loc_d = rand_elem(LOCAIS)
    
    if is_uber:
        uber_count += 1
        cat = 'UberX' if random.random() > 0.4 else ('Comfort' if random.random() > 0.3 else 'Uber Black')
        is_dyn = random.random() < 0.25
        dyn_val = round(rand_float(3.50, 14.20), 2)
        all_rides.append({
            "app": "uber", "start_hm": start_hm, "end_hm": end_hm, "valor": val, "km": km,
            "cat": cat, "is_dyn": is_dyn, "dyn_val": dyn_val, "mins": mins, "sec": sec,
            "origem": loc_o, "destino": loc_d
        })
    else:
        n99_count += 1
        cat = 'Pop' if random.random() > 0.5 else 'Pop Expresso'
        all_rides.append({
            "app": "n99", "start_hm": start_hm, "end_hm": end_hm, "valor": val, "cat": cat,
            "origem": loc_o, "destino": loc_d
        })
        
    # Salto para próxima corrida (batendo lata/deslocamento) entre 2 e 15 minutos
    current_time = end_t + timedelta(minutes=rand_int(2, 15))

# Separar rides
uber_rides = [r for r in all_rides if r['app'] == 'uber']
n99_rides = [r for r in all_rides if r['app'] == 'n99']

# Sort para exibição no HTML (inverso, do mais recente pro mais antigo, igual original)
uber_rides.reverse()
n99_rides.reverse()

# Gerar HTML
uber_html = ""
for c in uber_rides:
    dyn_html = f'<div class="uber-dynamic-pill">⚡ R$ {str(c["dyn_val"]).replace(".",",")} Preço dinâmico</div>' if c['is_dyn'] else ''
    uber_html += f"""
          <div class="uber-trip-card">
            <div class="uber-trip-header">
              <div>
                <div class="uber-price-main">R$ {str(c['valor']).replace('.',',')}</div>
                <div class="uber-category-meta">{c['cat']} &middot; {c['mins']} min {c['sec']} segundos &middot; {c['km']} km</div>
                {dyn_html}
              </div>
              <div class="uber-time-badge">{c['end_hm']}</div>
            </div>
            <div class="uber-map-thumb">
              <svg class="uber-map-svg" viewBox="0 0 300 100" preserveAspectRatio="none">
                <path d="M 20 80 Q 150 {rand_int(10,90)} 280 20" stroke="#000000" stroke-width="4" fill="none" stroke-dasharray="6,4"/>
              </svg>
            </div>
            <div class="uber-route-addresses">
              <div class="uber-addr-item"><div class="pin-circle-green"></div><div class="uber-addr-text">{c['origem']['rua']}, {c['origem']['bairro']}</div></div>
              <div class="uber-addr-item"><div class="pin-square-red"></div><div class="uber-addr-text">{c['destino']['rua']}, {c['destino']['bairro']}</div></div>
            </div>
          </div>
"""

n99_html = ""
for c in n99_rides:
    n99_html += f"""
          <div class="n99-card">
            <div style="font-size:12px; color:#888888; display:flex; justify-content:space-between;">
              <span>Ganhos pagos no app</span>
              <span>{c['end_hm']}</span>
            </div>
            <div class="n99-card-top">
              <div class="n99-product"><div class="n99-product-icon">99</div><span>{c['cat']}</span></div>
              <div class="n99-price">R$ {str(c['valor']).replace('.',',')} &rsaquo;</div>
            </div>
            <div class="n99-route-node"><div class="n99-dot"></div><div class="n99-addr-text">{c['origem']['rua']}, {c['origem']['bairro']}</div></div>
            <div class="n99-route-node"><div class="n99-dot dest"></div><div class="n99-addr-text">{c['destino']['rua']}, {c['destino']['bairro']}</div></div>
            <div class="n99-status-pago"><span>&checkmark; Pago</span></div>
          </div>
"""

with open("/home/claus/src/app_jornada/simulador-pwa/index.html", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"function generateUberRides\(\) \{.*?(?=function generate99Rides)",
    f"""function generateUberRides() {{
      const container = document.getElementById('uber-list-container');
      let html = '<div class="uber-section-date">sex., 7 de ago.</div>';
      html += `{uber_html}`;
      container.innerHTML = html;
    }}
    
    """,
    content, flags=re.DOTALL
)

content = re.sub(
    r"function generate99Rides\(\) \{.*?(?=function switchMode)",
    f"""function generate99Rides() {{
      const container = document.getElementById('n99-list-container');
      let html = '<div class="n99-date-bar">07/08/2026</div>';
      html += `{n99_html}`;
      container.innerHTML = html;
    }}
    
    """,
    content, flags=re.DOTALL
)

with open("/home/claus/src/app_jornada/simulador-pwa/index.html", "w", encoding="utf-8") as f:
    f.write(content)

def parse_time(hm):
    h, m = map(int, hm.split(":"))
    return datetime(2026, 8, 7, h, m, 0)

telemetria = []
current_time = datetime(2026, 8, 7, 6, 0, 0)
end_time = datetime(2026, 8, 7, 19, 0, 0)

# Sort all rides chronologically by start time
sorted_rides = sorted(all_rides, key=lambda x: parse_time(x['start_hm']))

def get_status_at(t):
    for c in sorted_rides:
        st = parse_time(c['start_hm'])
        et = parse_time(c['end_hm'])
        if st <= t <= et:
            return "CORRIDA", c['origem'], c['destino'], st, et
        
        # 5 minutes before ride = deslocamento
        desloc_start = st - timedelta(minutes=5)
        if desloc_start <= t < st:
            return "DESLOCAMENTO", LOCAIS[0], c['origem'], desloc_start, st
    
    # Otherwise batendo lata or parado
    # If it's night, parado
    if t > datetime(2026, 8, 7, 18, 55, 0):
        return "PARADO", LOCAIS[0], LOCAIS[0], t, t+timedelta(minutes=1)
        
    return "BATENDO_LATA", LOCAIS[0], LOCAIS[0], t, t+timedelta(minutes=1)

import requests

def get_osrm_route(loc1, loc2):
    try:
        url = f"http://2.24.121.189:5000/route/v1/driving/{loc1['lon']},{loc1['lat']};{loc2['lon']},{loc2['lat']}?geometries=geojson"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data["code"] == "Ok":
                coords = data["routes"][0]["geometry"]["coordinates"]
                return coords # list of [lon, lat]
    except Exception:
        pass
    return [[loc1['lon'], loc1['lat']], [loc2['lon'], loc2['lat']]]

def get_coord_along_route(coords, frac):
    if not coords: return 0, 0
    if len(coords) == 1: return coords[0][1], coords[0][0]
    
    # Calculate total length (rough euclidean for interpolation)
    segs = []
    tot = 0
    for i in range(len(coords)-1):
        dx = coords[i+1][0] - coords[i][0]
        dy = coords[i+1][1] - coords[i][1]
        d = (dx*dx + dy*dy)**0.5
        segs.append(d)
        tot += d
        
    if tot == 0: return coords[0][1], coords[0][0]
    
    target = tot * frac
    curr = 0
    for i in range(len(segs)):
        if curr + segs[i] >= target:
            # interpolate within this segment
            rem = target - curr
            f = rem / segs[i] if segs[i] > 0 else 0
            lon = coords[i][0] + (coords[i+1][0] - coords[i][0]) * f
            lat = coords[i][1] + (coords[i+1][1] - coords[i][1]) * f
            return lat, lon
        curr += segs[i]
    return coords[-1][1], coords[-1][0]

osrm_cache = {}

while current_time <= end_time:
    status_type, loc_orig, loc_dest, st, et = get_status_at(current_time)
    
    if status_type in ["CORRIDA", "DESLOCAMENTO"]:
        total_seconds = (et - st).total_seconds()
        if total_seconds == 0: total_seconds = 1
        elapsed = (current_time - st).total_seconds()
        frac = elapsed / total_seconds
        
        # Cache OSRM route to avoid duplicate calls for same segment
        cache_key = f"{loc_orig['lat']},{loc_orig['lon']}-{loc_dest['lat']},{loc_dest['lon']}"
        if cache_key not in osrm_cache:
            osrm_cache[cache_key] = get_osrm_route(loc_orig, loc_dest)
            
        coords = osrm_cache[cache_key]
        lat, lon = get_coord_along_route(coords, frac)
        status = "CONDUZINDO"
        dist = 800.0
    else:
        lat = loc_orig["lat"]
        lon = loc_orig["lon"]
        status = "PARADO"
        if status_type == "BATENDO_LATA":
            status = "CONDUZINDO"
            lat += random.uniform(-0.002, 0.002)
            lon += random.uniform(-0.002, 0.002)
        dist = 0 if status == "PARADO" else 150.0
        
    telemetria.append({
        "time": current_time.strftime("%H:%M:%S"),
        "lat": lat,
        "lon": lon,
        "status": status,
        "dist": dist / 4.0
    })
    
    current_time += timedelta(seconds=15)

with open("/home/claus/src/app_jornada/scripts/populate_dense.py", "w") as f:
    f.write(f'''
import asyncio
from datetime import datetime, timezone
import json
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from bson import ObjectId

async def run():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client.get_database()
    j_id = "Clausemberg Rodrigues de Olvierira-TEST-1234-07082026150119"
    await db["historico_gps"].delete_many({{"jornada_id": j_id}})
    
    base = datetime(2026, 8, 7, tzinfo=timezone.utc)
    docs = []
    
    telemetria_data = {json.dumps(telemetria)}
    
    for t in telemetria_data:
        h, m, s = map(int, t["time"].split(":"))
        detalhes = f"{{t['status']}} | Deslocamento | Dist: {{t['dist']/1000:.1f}}km"
        docs.append({{
            "jornada_id": j_id,
            "motorista_id": ObjectId("6a40670ec7008f9c4eeb44e2"),
            "timestamp": base.replace(hour=h, minute=m, second=s),
            "localizacao": {{"type": "Point", "coordinates": [t["lon"], t["lat"]]}},
            "lat": t["lat"],
            "lon": t["lon"],
            "status": t["status"],
            "detalhes": detalhes,
            "distancia_ultima_m": t["dist"],
            "tipo": "TELEMETRIA_GPS"
        }})
        
    await db["historico_gps"].insert_many(docs)
    print(f"Inseridos {{len(docs)}} pontos densos de telemetria baseados em 100 corridas (50 Uber, 50 99)!")
    
asyncio.run(run())
''')

print("Gerado script!")
