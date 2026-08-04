"""
route_tracer.py — Serviço para traçar rotas produtivas via Google Directions API.

Quando um comprovante de corrida é registrado (com origem/destino),
este serviço:
1. Usa Google Directions API para obter a polyline da rota real
2. Decodifica a polyline em pontos GPS
3. Insere esses pontos como `produtivo: True` no historico_gps
4. Quando a jornada for encerrada, os segmentos_rota terão
   a separação correta entre km produtiva e km morta.
"""

import httpx
import os
import math
from typing import Optional, Tuple, List
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.services.matching import geocode_address


async def obter_rota_google(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    api_key: str,
) -> Optional[dict]:
    """
    Chama Google Directions API para obter a rota entre dois pontos.
    Retorna dict com 'polyline' (encoded), 'distance_m', 'duration_s', e 'steps'.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lon}",
        "destination": f"{dest_lat},{dest_lon}",
        "mode": "driving",
        "key": api_key,
        "region": "br",
        "language": "pt-BR",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                print(f"[ROUTE_TRACER] Google Directions HTTP {resp.status_code}")
                return None

            data = resp.json()
            if data.get("status") != "OK" or not data.get("routes"):
                print(f"[ROUTE_TRACER] Google Directions status: {data.get('status')}")
                return None

            route = data["routes"][0]
            leg = route["legs"][0]

            return {
                "overview_polyline": route["overview_polyline"]["points"],
                "distance_m": leg["distance"]["value"],
                "duration_s": leg["duration"]["value"],
                "start_address": leg.get("start_address", ""),
                "end_address": leg.get("end_address", ""),
            }
        except Exception as e:
            print(f"[ROUTE_TRACER] Erro ao chamar Google Directions: {e}")
            return None


def decode_polyline_to_points(encoded: str) -> List[Tuple[float, float]]:
    """Decodifica uma polyline do Google em lista de (lat, lon)."""
    points = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Decodifica latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = (~(result >> 1)) if (result & 1) else (result >> 1)
        lat += dlat

        # Decodifica longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = (~(result >> 1)) if (result & 1) else (result >> 1)
        lng += dlng

        points.append((lat / 1e5, lng / 1e5))

    return points


async def tracar_rota_produtiva(
    jornada_id: str,
    motorista_id: str,
    start_lat: Optional[float],
    start_lon: Optional[float],
    end_lat: Optional[float],
    end_lon: Optional[float],
    start_time_ms: Optional[int],
    end_time_ms: Optional[int],
    origem_texto: Optional[str],
    destino_texto: Optional[str],
    comprovante_url: str,
):
    """
    Traça a rota produtiva de uma corrida via Google Directions API
    e insere os pontos como produtivos no historico_gps.

    Se coordenadas não forem fornecidas, geocodifica os nomes de rua.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ROUTE_TRACER] GOOGLE_API_KEY não configurada")
        return

    db = get_db()

    # Resolver coordenadas de origem
    o_lat, o_lon = start_lat, start_lon
    if o_lat is None or o_lon is None:
        if origem_texto:
            coords = await geocode_address(origem_texto, api_key)
            if coords:
                o_lat, o_lon = coords
                print(f"[ROUTE_TRACER] Origem geocodificada: {origem_texto} → ({o_lat}, {o_lon})")

    # Resolver coordenadas de destino
    d_lat, d_lon = end_lat, end_lon
    if d_lat is None or d_lon is None:
        if destino_texto:
            coords = await geocode_address(destino_texto, api_key)
            if coords:
                d_lat, d_lon = coords
                print(f"[ROUTE_TRACER] Destino geocodificado: {destino_texto} → ({d_lat}, {d_lon})")

    if o_lat is None or o_lon is None or d_lat is None or d_lon is None:
        print(f"[ROUTE_TRACER] Não foi possível resolver coordenadas para a corrida. Abortando.")
        return

    # Chamar Google Directions API
    rota = await obter_rota_google(o_lat, o_lon, d_lat, d_lon, api_key)
    if not rota:
        print(f"[ROUTE_TRACER] Google Directions não retornou rota. Abortando.")
        return

    polyline_encoded = rota["overview_polyline"]
    pontos_rota = decode_polyline_to_points(polyline_encoded)

    if len(pontos_rota) < 2:
        print(f"[ROUTE_TRACER] Polyline decodificada com menos de 2 pontos. Abortando.")
        return

    print(f"[ROUTE_TRACER] Rota obtida: {len(pontos_rota)} pontos, "
          f"{rota['distance_m']}m, {rota['duration_s']}s")

    # Determinar timestamps para interpolar os pontos
    if start_time_ms and end_time_ms:
        t_start = datetime.fromtimestamp(start_time_ms / 1000.0, tz=timezone.utc)
        t_end = datetime.fromtimestamp(end_time_ms / 1000.0, tz=timezone.utc)
    else:
        # Sem timestamps, usar o timestamp da jornada + data_hora do comprovante
        # ou um horário estimado
        t_start = datetime.now(timezone.utc) - timedelta(seconds=rota["duration_s"])
        t_end = datetime.now(timezone.utc)

    total_pts = len(pontos_rota)
    duration_total = (t_end - t_start).total_seconds()
    step_s = duration_total / max(1, total_pts - 1)

    # Limpar pontos existentes no intervalo de tempo (se houver)
    try:
        delete_result = await db["historico_gps"].delete_many({
            "jornada_id": jornada_id,
            "timestamp": {"$gte": t_start, "$lte": t_end}
        })
        if delete_result.deleted_count > 0:
            print(f"[ROUTE_TRACER] Removidos {delete_result.deleted_count} pontos sobrepostos no intervalo")
    except Exception as e:
        print(f"[ROUTE_TRACER] Erro ao limpar pontos sobrepostos: {e}")

    # Inserir pontos produtivos
    from bson import ObjectId
    docs = []
    for idx, (lat, lon) in enumerate(pontos_rota):
        pt_time = t_start + timedelta(seconds=idx * step_s)
        docs.append({
            "motorista_id": ObjectId(motorista_id),
            "jornada_id": jornada_id,
            "timestamp": pt_time,
            "localizacao": {
                "type": "Point",
                "coordinates": [lon, lat]  # GeoJSON: [lon, lat]
            },
            "distancia_ultima_m": 0.0,
            "status": "CONDUZINDO",
            "rua": "Via Google Directions",
            "contador_mesclados": 1,
            "produtivo": True,
            "fonte": "google_directions",
            "comprovante_url": comprovante_url,
        })

    if docs:
        await db["historico_gps"].insert_many(docs)
        print(f"[ROUTE_TRACER] ✅ Inseridos {len(docs)} pontos produtivos "
              f"(Google Directions) na jornada {jornada_id}")

    # Atualizar status do match no comprovante
    try:
        doc = await db["jornadas"].find_one({"_id": jornada_id})
        if doc and "faturamento" in doc:
            fat = doc["faturamento"]
            if "comprovantes_processados" in fat:
                for item in fat["comprovantes_processados"]:
                    if item.get("url_comprovante") == comprovante_url:
                        item["match_produtivo_status"] = "SUCESSO_GOOGLE_DIRECTIONS"
                await db["jornadas"].update_one(
                    {"_id": jornada_id},
                    {"$set": {"faturamento": fat}}
                )
    except Exception as e:
        print(f"[ROUTE_TRACER] Erro ao atualizar status do match: {e}")

    return {
        "pontos_inseridos": len(docs),
        "distancia_m": rota["distance_m"],
        "duracao_s": rota["duration_s"],
    }
