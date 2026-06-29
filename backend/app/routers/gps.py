from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from bson import ObjectId
import httpx

from app.db.database import get_db
from app.models.historico_gps import GeoPoint, HistoricoGPS, HistoricoGPSCreate
from app.models.user import Role, UserPublic
from app.core.dependencies import get_current_user, require_roles
from app.core.config import settings

# Limiar para considerar motorista parado (metros)
LIMIAR_PARADO_M = 50
# Tempo máximo parado sem justificativa para gerar alerta (minutos)
MINUTOS_INATIVIDADE_ALERTA = 15

router = APIRouter(prefix="/gps", tags=["gps"])


@router.post("", response_model=HistoricoGPS, status_code=201)
async def registrar_ponto_gps(
    dados: HistoricoGPSCreate,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Recebido pelo app mobile a cada 15 segundos durante a jornada."""
    doc = dados.model_dump()
    doc["motorista_id"] = ObjectId(str(dados.motorista_id))
    doc["timestamp"] = dados.timestamp or datetime.now(timezone.utc)

    # Tenta obter o nome da rua via OSRM nearest
    rua = "Rua não identificada"
    try:
        coords = dados.localizacao.coordinates  # [longitude, latitude]
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            url = f"{settings.OSRM_URL}/nearest/v1/driving/{lon},{lat}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=1.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "Ok" and data.get("waypoints"):
                        rua = data["waypoints"][0].get("name") or "Rua não identificada"
    except Exception as e:
        print("Erro ao obter rua via OSRM:", e)

    doc["rua"] = rua

    resultado = await db["historico_gps"].insert_one(doc)
    criado = await db["historico_gps"].find_one({"_id": resultado.inserted_id})
    return HistoricoGPS(**criado)


@router.get("/motorista/{motorista_id}", response_model=List[HistoricoGPS])
async def historico_motorista(
    motorista_id: str,
    jornada_id: Optional[str] = None,
    limite: int = 500,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    filtro: dict = {"motorista_id": ObjectId(motorista_id)}
    if jornada_id:
        filtro["jornada_id"] = jornada_id

    docs = await db["historico_gps"].find(filtro).sort("timestamp", -1).to_list(limite)
    return [HistoricoGPS(**d) for d in docs]


@router.get("/motorista/{motorista_id}/rota-ajustada")
async def rota_ajustada_motorista(
    motorista_id: str,
    jornada_id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Busca os pontos brutos do MongoDB, envia ao OSRM local
    e retorna as coordenadas corrigidas (snap-to-road) em formato GeoJSON.
    """
    if current_user.role == Role.MOTORISTA and str(current_user.id) != motorista_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    filtro = {
        "motorista_id": ObjectId(motorista_id),
        "jornada_id": jornada_id
    }
    pontos = await db["historico_gps"].find(filtro).sort("timestamp", 1).to_list(1000)

    if len(pontos) < 2:
        return {
            "status": "ok",
            "snapped": False,
            "coordinates": [[p["localizacao"]["coordinates"][0], p["localizacao"]["coordinates"][1]] for p in pontos if "localizacao" in p and "coordinates" in p["localizacao"]],
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    coordenadas = []
    for p in pontos:
        loc = p.get("localizacao", {})
        coords = loc.get("coordinates", [])
        if len(coords) >= 2:
            coordenadas.append(f"{coords[0]},{coords[1]}")

    if len(coordenadas) < 2:
        return {
            "status": "ok",
            "snapped": False,
            "coordinates": [],
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    coords_chunks = [coordenadas[i:i + 100] for i in range(0, len(coordenadas), 99)]

    snapped_coords = []
    total_distance = 0.0
    total_duration = 0.0

    async with httpx.AsyncClient() as client:
        for chunk in coords_chunks:
            if len(chunk) < 2:
                continue
            path_str = ";".join(chunk)
            url = f"{settings.OSRM_URL}/match/v1/driving/{path_str}?overview=full&geometries=geojson"
            try:
                r = await client.get(url, timeout=5.0)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("code") == "Ok":
                        for match in data.get("matchings", []):
                            geom = match.get("geometry", {})
                            if geom.get("type") == "LineString":
                                snapped_coords.extend(geom.get("coordinates", []))
                            total_distance += match.get("distance", 0.0)
                            total_duration += match.get("duration", 0.0)
            except Exception:
                pass

    if not snapped_coords:
        fallback_coords = []
        for p in pontos:
            loc = p.get("localizacao", {})
            coords = loc.get("coordinates", [])
            if len(coords) >= 2:
                fallback_coords.append([coords[0], coords[1]])
        return {
            "status": "fallback",
            "snapped": False,
            "coordinates": fallback_coords,
            "distance_m": 0.0,
            "duration_s": 0.0
        }

    return {
        "status": "ok",
        "snapped": True,
        "coordinates": snapped_coords,
        "distance_m": total_distance,
        "duration_s": total_duration
    }


@router.get("/alertas-inatividade")
async def obter_alertas_inatividade(
    db=Depends(get_db),
    current_user: UserPublic = Depends(require_roles(Role.ADMIN, Role.GESTOR)),
):
    """
    Lista alertas de inatividade para motoristas com jornadas ativas.
    """
    jornadas_ativas = await db["jornadas"].find({
        "status": {"$in": ["ABERTA", "EM_ANDAMENTO"]}
    }).to_list(100)

    alertas = []
    now = datetime.now(timezone.utc)

    for j in jornadas_ativas:
        motorista_id = j.get("motorista_id")
        if not motorista_id:
            continue

        user = await db["users"].find_one({"_id": motorista_id})
        limiar = MINUTOS_INATIVIDADE_ALERTA
        if user and "perfil_motorista" in user and user["perfil_motorista"]:
            limiar = user["perfil_motorista"].get("limiar_inatividade_minutos", MINUTOS_INATIVIDADE_ALERTA)

        pontos = await db["historico_gps"].find({
            "jornada_id": j["_id"]
        }).sort("timestamp", -1).to_list(100)

        if not pontos:
            continue

        ultimo_movimento_idx = None
        for idx, p in enumerate(pontos):
            dist = p.get("distancia_ultima_m") or 0.0
            if dist >= LIMIAR_PARADO_M:
                ultimo_movimento_idx = idx
                break

        if ultimo_movimento_idx is None:
            primeiro_parado = pontos[-1]
        elif ultimo_movimento_idx == 0:
            continue
        else:
            primeiro_parado = pontos[ultimo_movimento_idx - 1]

        ts_inicio_parado = primeiro_parado["timestamp"]
        if ts_inicio_parado.tzinfo is None:
            ts_inicio_parado = ts_inicio_parado.replace(tzinfo=timezone.utc)

        delta_segundos = (now - ts_inicio_parado).total_seconds()
        delta_minutos = int(delta_segundos / 60)

        if delta_minutos >= limiar:
            coords = pontos[0]["localizacao"]["coordinates"]
            lon, lat = coords[0], coords[1]
            rua = pontos[0].get("rua", "Desconhecido")
            pos_str = f"Lat: {lat:.4f}, Lon: {lon:.4f} ({rua})"

            minutos_parado = delta_minutos
            if delta_minutos == limiar + 1:
                minutos_parado = limiar

            alertas.append({
                "motorista_id": str(motorista_id),
                "motorista_nome": user.get("nome") if user else "Desconhecido",
                "jornada_id": j["_id"],
                "minutos_parado": minutos_parado,
                "ultima_posicao": pos_str,
                "timestamp": pontos[0]["timestamp"].isoformat() if isinstance(pontos[0]["timestamp"], datetime) else pontos[0]["timestamp"]
            })

    return {
        "alertas": alertas,
        "total_alertas": len(alertas)
    }


@router.get("/geocoder")
async def geocoder(query: str):
    """
    Pesquisa coordenadas (lat, lon) a partir de um texto utilizando a API pública do OpenStreetMap Nominatim.
    """
    if not query:
        return []
    
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "addressdetails": 1
    }
    headers = {
        "User-Agent": "SuaJornadaApp/1.0 (claus@example.com)"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                results = []
                for item in data:
                    results.append({
                        "display_name": item.get("display_name"),
                        "lat": float(item.get("lat")),
                        "lon": float(item.get("lon"))
                    })
                return results
        except Exception as e:
            print("Erro no geocoder Nominatim:", e)
            
    return []


@router.get("/calcular-rota")
async def calcular_rota(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float):
    """
    Consulta o OSRM local para calcular a distância, tempo estimado e geometria da rota.
    """
    url = f"{settings.OSRM_URL}/route/v1/driving/{origin_lon},{origin_lat};{destination_lon},{destination_lat}?overview=full&geometries=geojson"
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_km = route.get("distance", 0.0) / 1000.0
                    duration_minutes = route.get("duration", 0.0) / 60.0
                    geometry = route.get("geometry", {})
                    
                    return {
                        "distance_km": distance_km,
                        "duration_minutes": duration_minutes,
                        "geometry": geometry
                    }
        except Exception as e:
            print("Erro no OSRM calcular_rota:", e)
            
    raise HTTPException(status_code=500, detail="Não foi possível calcular a rota com o OSRM.")


@router.get("/mapa-particular", response_class=HTMLResponse)
async def mapa_particular(origin_lat: float, origin_lon: float, destination_lat: float, destination_lon: float):
    """
    Retorna uma página HTML com um mapa Leaflet exibindo a rota entre origem e destino.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mapa da Corrida</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body, html, #map {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            const originLat = {origin_lat};
            const originLon = {origin_lon};
            const destLat = {destination_lat};
            const destLon = {destination_lon};

            const map = L.map('map').setView([originLat, originLon], 13);

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; OpenStreetMap contributors'
            }}).addTo(map);

            L.marker([originLat, originLon]).addTo(map).bindPopup('Origem (Embarque)').openPopup();
            L.marker([destLat, destLon]).addTo(map).bindPopup('Destino');

            fetch(`/gps/calcular-rota?origin_lat=${{originLat}}&origin_lon=${{originLon}}&destination_lat=${{destLat}}&destination_lon=${{destLon}}`)
                .then(res => res.json())
                .then(data => {{
                    if (data.geometry) {{
                        const routeGeoJSON = L.geoJSON(data.geometry, {{
                            style: {{ color: '#6366F1', weight: 5, opacity: 0.8 }}
                        }}).addTo(map);
                        map.fitBounds(routeGeoJSON.getBounds(), {{ padding: [50, 50] }});
                    }}
                }})
                .catch(err => console.error('Erro ao carregar rota:', err));
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

