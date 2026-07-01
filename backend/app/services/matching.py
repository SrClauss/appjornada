import httpx
import os
import math
from typing import List, Tuple, Optional
from datetime import datetime, timezone

from app.db.database import get_db
from app.routers.jornadas import encode_polyline
import re
import unicodedata

def normalizar_rua(nome: str) -> str:
    if not nome:
        return ""
    n = nome.lower()
    # Substituir abreviações comuns de logradouros
    n = re.sub(r'\b(av|avenida|av\.)\b', 'av', n)
    n = re.sub(r'\b(r|rua|r\.)\b', 'rua', n)
    n = re.sub(r'\b(dr|doutor|dr\.)\b', 'dr', n)
    n = re.sub(r'\b(prof|professor|prof\.)\b', 'prof', n)
    # Remover números e CEPs comuns para focar apenas no nome da rua
    n = re.sub(r'\b\d+\b', '', n)
    # Remover acentos
    n = "".join(c for c in unicodedata.normalize('NFD', n) if unicodedata.category(c) != 'Mn')
    # Remover caracteres especiais
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def ruas_compativeis(rua_ia: str, rua_gps: str) -> bool:
    if not rua_ia or not rua_gps:
        return False
    norm_ia = normalizar_rua(rua_ia)
    norm_gps = normalizar_rua(rua_gps)
    if not norm_ia or not norm_gps:
        return False
    # Checar se o nome de uma está contido na outra
    return norm_ia in norm_gps or norm_gps in norm_ia

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def geocode_address(address: str, api_key: str) -> Optional[Tuple[float, float]]:
    if not address or len(address.strip()) < 3:
        return None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": f"{address}, Brasil", "key": api_key, "region": "br"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "OK" and data.get("results"):
                    location = data["results"][0]["geometry"]["location"]
                    return location["lat"], location["lng"]
        except Exception as e:
            print(f"[MATCHING] Erro Geocoding: {e}")
            pass
    return None

async def calcular_match_produtivo(
    jornada_id: str,
    comprovante_url: str,
    origem: str,
    destino: str,
    data_hora: str = None
):
    """
    Executado em background. Encontra o segmento GPS e atualiza a jornada.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(f"[MATCHING] Erro: GOOGLE_API_KEY não configurada.")
        await _marcar_falha_match(jornada_id, comprovante_url)
        return

    print(f"[MATCHING] Iniciando match geospacial para comprovante {comprovante_url}")
    coord_origem = await geocode_address(origem, api_key)
    coord_destino = await geocode_address(destino, api_key)

    # Se falhar a geocodificação, usaremos apenas a busca textual de ruas.
    if not coord_origem:
        print(f"[MATCHING] Geocodificação vazia para Origem ({origem}). Usando apenas match textual da rua.")
    if not coord_destino:
        print(f"[MATCHING] Geocodificação vazia para Destino ({destino}). Usando apenas match textual da rua.")

    db = get_db()
    
    # Buscar pontos GPS brutos
    pontos = await db["historico_gps"].find({"jornada_id": jornada_id}).sort("timestamp", 1).to_list(20000)
    
    if not pontos:
        print(f"[MATCHING] Nenhum ponto GPS bruto encontrado para a jornada {jornada_id}. Match abortado.")
        await _marcar_falha_match(jornada_id, comprovante_url)
        return

    idx_origem = -1
    idx_destino = -1

    # -------------------------------------------------------------------------
    # PASSO 1: PESQUISA POR RUA (PRIMEIRA PESQUISA)
    # -------------------------------------------------------------------------
    # Encontrar todos os pontos que batem com a rua de origem
    pontos_rua_origem = []
    for i, p in enumerate(pontos):
        if ruas_compativeis(origem, p.get("rua", "")):
            pontos_rua_origem.append((i, p))

    # Se encontramos pontos na rua de origem, percorremos eles para achar o que faz mais sentido
    if pontos_rua_origem:
        min_dist_orig = float('inf')
        for i, p in pontos_rua_origem:
            loc = p.get("localizacao", {})
            coords = loc.get("coordinates", [])
            if len(coords) >= 2:
                lat, lon = coords[1], coords[0]
                dist = _haversine(coord_origem[0], coord_origem[1], lat, lon) if coord_origem else 0.0
                # Preferimos o ponto mais próximo da coordenada geocodificada na rua
                if dist < min_dist_orig:
                    min_dist_orig = dist
                    idx_origem = i
        print(f"[MATCHING] Origem detectada via busca primária por Rua (índice {idx_origem}, dist={min_dist_orig:.1f}m)")

    # Encontrar todos os pontos que batem com a rua de destino subsequentes à origem
    if idx_origem != -1:
        pontos_rua_destino = []
        for i in range(idx_origem, len(pontos)):
            p = pontos[i]
            if ruas_compativeis(destino, p.get("rua", "")):
                pontos_rua_destino.append((i, p))

        if pontos_rua_destino:
            min_dist_dest = float('inf')
            for i, p in pontos_rua_destino:
                loc = p.get("localizacao", {})
                coords = loc.get("coordinates", [])
                if len(coords) >= 2:
                    lat, lon = coords[1], coords[0]
                    dist = _haversine(coord_destino[0], coord_destino[1], lat, lon) if coord_destino else 0.0
                    if dist < min_dist_dest:
                        min_dist_dest = dist
                        idx_destino = i
            print(f"[MATCHING] Destino detectado via busca primária por Rua (índice {idx_destino}, dist={min_dist_dest:.1f}m)")

    # -------------------------------------------------------------------------
    # PASSO 2: FALLBACK PARA PESQUISA POR RAIO DE GPS PURO
    # -------------------------------------------------------------------------
    # Só roda se a busca primária por rua não conseguiu casar a corrida
    if idx_origem == -1 or idx_destino == -1:
        print("[MATCHING] Busca por rua falhou ou incompleta. Iniciando Fallback por Raio de GPS...")
        raios = [1, 5, 10, 20, 25, 50, 100]
        idx_origem = -1
        idx_destino = -1
        
        for r in raios:
            orig_candidate = -1
            min_dist_orig = float('inf')
            for i, p in enumerate(pontos):
                loc = p.get("localizacao", {})
                coords = loc.get("coordinates", [])
                if len(coords) >= 2:
                    lat, lon = coords[1], coords[0]
                    dist = _haversine(coord_origem[0], coord_origem[1], lat, lon) if coord_origem else float('inf')
                    if dist <= r and dist < min_dist_orig:
                        min_dist_orig = dist
                        orig_candidate = i
            
            if orig_candidate == -1:
                continue
                
            dest_candidate = -1
            min_dist_dest = float('inf')
            for i in range(orig_candidate, len(pontos)):
                p = pontos[i]
                loc = p.get("localizacao", {})
                coords = loc.get("coordinates", [])
                if len(coords) >= 2:
                    lat, lon = coords[1], coords[0]
                    dist = _haversine(coord_destino[0], coord_destino[1], lat, lon) if coord_destino else float('inf')
                    if dist <= r and dist < min_dist_dest:
                        min_dist_dest = dist
                        dest_candidate = i
            
            if dest_candidate != -1:
                idx_origem = orig_candidate
                idx_destino = dest_candidate
                print(f"[MATCHING] Match bem-sucedido via Fallback de Raio de GPS em {r}m.")
                break

    if idx_origem == -1 or idx_destino == -1:
        print(f"[MATCHING] Falha: Não foi possível casar origem e destino sob nenhum método (Rua ou Raio).")
        await _marcar_falha_match(jornada_id, comprovante_url)
        return

    # Se por acaso o idx_origem e idx_destino forem o mesmo ponto (corrida super curta)
    if idx_origem == idx_destino:
        idx_destino = min(idx_destino + 1, len(pontos) - 1)

    # Coletar IDs dos pontos que pertencem a esse deslocamento produtivo
    ids_produtivos = []
    for i in range(idx_origem, idx_destino + 1):
        ids_produtivos.append(pontos[i]["_id"])

    if not ids_produtivos:
        await _marcar_falha_match(jornada_id, comprovante_url)
        return

    # MUDANÇA NOS DADOS: Marcar diretamente os pontos GPS brutos como produtivos
    result = await db["historico_gps"].update_many(
        {"_id": {"$in": ids_produtivos}},
        {"$set": {"produtivo": True}}
    )
    
    # Atualizar o status do comprovante para SUCESSO
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$set": {"faturamento.comprovantes_processados.$[elem].match_produtivo_status": "SUCESSO"}},
        array_filters=[{"elem.url_comprovante": comprovante_url}]
    )
    
    print(f"[MATCHING] Sucesso! {result.modified_count} pontos de GPS marcados como produtivos na jornada {jornada_id}")

async def _marcar_falha_match(jornada_id: str, comprovante_url: str):
    db = get_db()
    await db["jornadas"].update_one(
        {"_id": jornada_id},
        {"$set": {"faturamento.comprovantes_processados.$[elem].match_produtivo_status": "FALHA"}},
        array_filters=[{"elem.url_comprovante": comprovante_url}]
    )


