import math
from typing import List, Dict, Any, Optional, Tuple


BASE_OPERACOES_PADRAO = (-20.26548, -40.29589)  # (lat, lon)


def calcular_distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Raio da Terra em metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def classificar_segmento(
    coords: List[Tuple[float, float]],  # List of (lat, lon)
    is_produtivo_flag: bool,
    proxima_corrida_inicio: Optional[Tuple[float, float]],
    base_coords: Tuple[float, float] = BASE_OPERACOES_PADRAO,
    tem_prestacao_contas: bool = True
) -> Dict[str, Any]:
    """
    Classifica um segmento de trajeto de acordo com as 5 regras de negócio:
    1. nao_identificado: Trajeto antes da prestação de contas.
    2. produtivo: Trajeto identificado como corrida.
    3. deslocamento: Trajeto deslocando para onde começa a próxima corrida.
    4. improdutivo_contra_base: Não é a favor de uma corrida e se distancia da base.
    5. improdutivo_a_favor_base: Não é a favor de uma corrida, mas aproxima da base.
    """
    if not coords or len(coords) < 2:
        return {
            "status": "nao_identificado",
            "rotulo": "Trajeto Não Identificado",
            "cor": "#94a3b8",
            "coords": coords
        }

    # 1. Se é uma corrida produtiva confirmada
    if is_produtivo_flag:
        return {
            "status": "produtivo",
            "rotulo": "Corrida Produtiva",
            "cor": "#10b981",  # Verde
            "coords": coords
        }

    # Se ainda não houve prestação de contas e não sabemos nada sobre corridas
    if not tem_prestacao_contas:
        return {
            "status": "nao_identificado",
            "rotulo": "Trajeto Não Identificado (Pré-prestação)",
            "cor": "#94a3b8",  # Cinza
            "coords": coords
        }

    p_inicio = coords[0]  # (lat, lon)
    p_fim = coords[-1]    # (lat, lon)

    # 2. Verificar se está deslocando a favor da próxima corrida
    if proxima_corrida_inicio:
        dist_inicio_a_corrida = calcular_distancia_m(p_inicio[0], p_inicio[1], proxima_corrida_inicio[0], proxima_corrida_inicio[1])
        dist_fim_a_corrida = calcular_distancia_m(p_fim[0], p_fim[1], proxima_corrida_inicio[0], proxima_corrida_inicio[1])

        # Se o trecho aproximou pelo menos 150m ou 20% da próxima corrida
        if dist_fim_a_corrida < dist_inicio_a_corrida - 150:
            return {
                "status": "deslocamento",
                "rotulo": "Deslocamento p/ Início de Corrida",
                "cor": "#f59e0b",  # Amarelo / Laranja
                "coords": coords
            }

    # 3. Analisar vetor em relação à Base de Operações
    dist_inicio_a_base = calcular_distancia_m(p_inicio[0], p_inicio[1], base_coords[0], base_coords[1])
    dist_fim_a_base = calcular_distancia_m(p_fim[0], p_fim[1], base_coords[0], base_coords[1])

    if dist_fim_a_base < dist_inicio_a_base - 100:
        # Aproximando da base
        return {
            "status": "improdutivo_a_favor_base",
            "rotulo": "Deslocamento em Direção à Base",
            "cor": "#3b82f6",  # Azul
            "coords": coords
        }
    else:
        # Afastando da base e sem ir para corrida
        return {
            "status": "improdutivo_contra_base",
            "rotulo": "Improdutivo (Afastando da Base)",
            "cor": "#ef4444",  # Vermelho
            "coords": coords
        }


def classificar_jornada_segmentos(
    pontos_gps: List[Dict[str, Any]],
    comprovantes: List[Dict[str, Any]],
    base_coords: Tuple[float, float] = BASE_OPERACOES_PADRAO
) -> List[Dict[str, Any]]:
    """
    Processa a lista completa de pontos de GPS de uma jornada e retorna
    os segmentos devidamente classificados com cores, rótulos e status.
    """
    if not pontos_gps or len(pontos_gps) < 2:
        return []

    tem_prestacao = len(comprovantes) > 0

    # Quebra de pontos em sub-segmentos baseados em flag produtivo ou mudanças de estado
    raw_segments = []
    curr_segment = []
    curr_flag = pontos_gps[0].get("produtivo", False)

    for p in pontos_gps:
        loc = p.get("localizacao", {})
        coords = loc.get("coordinates", [])
        if not coords or len(coords) < 2:
            continue
        lat, lon = coords[1], coords[0]
        p_flag = p.get("produtivo", False)

        if p_flag != curr_flag and len(curr_segment) > 0:
            curr_segment.append((lat, lon))
            raw_segments.append({"coords": curr_segment, "is_produtivo": curr_flag})
            curr_segment = [(lat, lon)]
            curr_flag = p_flag
        else:
            curr_segment.append((lat, lon))

    if len(curr_segment) > 1:
        raw_segments.append({"coords": curr_segment, "is_produtivo": curr_flag})

    # Descobrir origens de corridas futuras para vincular os deslocamentos
    pontos_inicio_corridas = []
    for idx, seg in enumerate(raw_segments):
        if seg["is_produtivo"] and len(seg["coords"]) > 0:
            pontos_inicio_corridas.append((idx, seg["coords"][0]))

    # Classificar cada segmento
    segmentos_classificados = []
    for idx, seg in enumerate(raw_segments):
        # Encontrar a próxima corrida a partir deste segmento
        proxima_corrida = None
        for corr_idx, pt_corrida in pontos_inicio_corridas:
            if corr_idx > idx:
                proxima_corrida = pt_corrida
                break

        res = classificar_segmento(
            coords=seg["coords"],
            is_produtivo_flag=seg["is_produtivo"],
            proxima_corrida_inicio=proxima_corrida,
            base_coords=base_coords,
            tem_prestacao_contas=tem_prestacao
        )
        segmentos_classificados.append(res)

    return segmentos_classificados
