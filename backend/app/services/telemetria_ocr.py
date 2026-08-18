import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

def _normalizar_texto(texto: str) -> str:
    """Normaliza o texto para facilitar a comparação lexical (minúsculas, remove pontuação básica)."""
    if not texto:
        return ""
    texto = texto.lower()
    # Remove acentos se necessário, ou pelo menos pontuação
    texto = re.sub(r'[,.\-/\(\)]', ' ', texto)
    return " ".join(texto.split())

def _calcular_similaridade_ruas(rua_telemetria: str, endereco_ocr: str) -> float:
    """
    Calcula similaridade de Jaccard simplificada baseada em palavras em comum.
    Em uma arquitetura madura, pode ser substituído por busca de distância entre
    as coordenadas do GPS e o resultado do geocoding do endereco_ocr.
    """
    if not rua_telemetria or not endereco_ocr:
        return 0.0
    
    palavras_tel = set(_normalizar_texto(rua_telemetria).split())
    palavras_ocr = set(_normalizar_texto(endereco_ocr).split())
    
    if not palavras_tel or not palavras_ocr:
        return 0.0
    
    intersecao = palavras_tel.intersection(palavras_ocr)
    # Ignora palavras muito curtas como preposições que podem inflacionar a similaridade
    stopwords = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "rua", "av", "avenida"}
    intersecao = {p for p in intersecao if p not in stopwords}
    palavras_tel_validas = {p for p in palavras_tel if p not in stopwords}
    
    if not palavras_tel_validas:
        return 0.0
        
    # Calcula a % de palavras relevantes da rua detectada pelo GPS que aparecem no OCR
    return len(intersecao) / len(palavras_tel_validas)

async def classificar_horario_corrida(
    db: AsyncIOMotorDatabase,
    motorista_id: str,
    data_str: str,
    horario_str: str,
    origem_ocr: str,
    destino_ocr: str,
    margem_minutos: int = 3
) -> Dict[str, Any]:
    """
    Cruza o horário (ex: '18:36') capturado pelo OCR com a telemetria do motorista.
    Objetivo: Identificar se o horário se refere ao INÍCIO ou ao FIM da corrida,
    baseando-se no endereço que o motorista estava fisicamente naquele horário.
    """
    try:
        if not horario_str or ':' not in horario_str:
            raise ValueError("Horário inválido ou ausente")

        hora, minuto = map(int, horario_str.split(':'))
        
        # Constrói o datetime assumindo horário local (ex: Brasília UTC-3)
        # Em um app real, o timezone idealmente vem da configuração da jornada ou do motorista.
        dt_local = datetime(
            year=int(data_str[0:4]), 
            month=int(data_str[5:7]), 
            day=int(data_str[8:10]), 
            hour=hora, 
            minute=minuto
        )
        
        # Converte para UTC (+3 horas no caso do Brasil) já que historico_gps salva em UTC.
        dt_utc = dt_local + timedelta(hours=3)
        
        start_time = dt_utc - timedelta(minutes=margem_minutos)
        end_time = dt_utc + timedelta(minutes=margem_minutos)
        
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S.999Z")

        # Busca pontos na telemetria
        pontos = await db.historico_gps.find({
            "motorista_id": motorista_id,
            "timestamp": {"$gte": start_str, "$lte": end_str}
        }).to_list(length=200)

        if not pontos:
            return {
                "classificacao": "DESCONHECIDO",
                "motivo": f"Sem dados de telemetria entre {start_time.strftime('%H:%M')} e {end_time.strftime('%H:%M')} UTC.",
                "rua_detectada": None
            }

        # Agrupa as ruas por onde ele passou no intervalo de +/- margem_minutos
        ruas_frequencia = {}
        for p in pontos:
            rua = p.get('rua')
            if rua and rua != "Rua não identificada":
                ruas_frequencia[rua] = ruas_frequencia.get(rua, 0) + 1
        
        if not ruas_frequencia:
            return {
                "classificacao": "DESCONHECIDO",
                "motivo": "Pontos de GPS encontrados, mas todos estavam sem rua identificada.",
                "rua_detectada": None
            }

        # Pega a rua onde o motorista passou mais tempo/gerou mais pontos no intervalo
        rua_principal = max(ruas_frequencia, key=ruas_frequencia.get)

        # Calcula a similaridade textual dessa rua contra a origem e destino do OCR
        sim_origem = _calcular_similaridade_ruas(rua_principal, origem_ocr)
        sim_destino = _calcular_similaridade_ruas(rua_principal, destino_ocr)

        classificacao = "DESCONHECIDO"
        if sim_origem > sim_destino and sim_origem >= 0.3:
            classificacao = "INICIO_DA_CORRIDA"
            motivo = f"A rua do GPS '{rua_principal}' teve maior similaridade com a Origem do OCR."
        elif sim_destino > sim_origem and sim_destino >= 0.3:
            classificacao = "FIM_DA_CORRIDA"
            motivo = f"A rua do GPS '{rua_principal}' teve maior similaridade com o Destino do OCR."
        elif sim_origem > 0 and sim_origem == sim_destino:
            classificacao = "AMBIGUO"
            motivo = f"A rua do GPS '{rua_principal}' possui similaridade igual para Origem e Destino."
        else:
            motivo = f"A rua do GPS '{rua_principal}' não tem palavras em comum suficientes com a Origem nem Destino."

        return {
            "classificacao": classificacao,
            "rua_detectada": rua_principal,
            "similaridade_origem": round(sim_origem, 3),
            "similaridade_destino": round(sim_destino, 3),
            "motivo": motivo
        }

    except Exception as e:
        return {
            "classificacao": "ERRO",
            "motivo": f"Falha interna: {str(e)}",
            "rua_detectada": None
        }

async def reconstruir_trajeto_corrida(
    db: AsyncIOMotorDatabase,
    motorista_id: str,
    data_str: str,
    horario_desembarque_str: str,
    origem_ocr: str,
    destino_ocr: str,
    janela_inicial_minutos: int = 40,
    janela_maxima_minutos: int = 180,
    horario_desembarque_anterior_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Regressa a partir do horário de Desembarque (ex: 16:36) buscando no histórico de GPS 
    o momento exato do Embarque (Origem) e Desembarque (Destino).
    
    Possui LÓGICA DE FALLBACK EXPANSIVA:
    Se a corrida durar mais de 40 minutos, expande a busca gradualmente (até 180 min ou até 
    o horário da corrida anterior) para não perder viagens longas ou intermunicipais.
    """
    try:
        if not horario_desembarque_str or ':' not in horario_desembarque_str:
            raise ValueError("Horário de desembarque inválido")

        hora, minuto = map(int, horario_desembarque_str.split(':'))
        dt_desembarque_local = datetime(int(data_str[0:4]), int(data_str[5:7]), int(data_str[8:10]), hora, minuto)
        dt_desembarque_utc = dt_desembarque_local + timedelta(hours=3)

        # Se houver corrida anterior identificada, define um limite inferior inteligente
        dt_limite_anterior_utc = None
        if horario_desembarque_anterior_str and ':' in horario_desembarque_anterior_str:
            h_ant, m_ant = map(int, horario_desembarque_anterior_str.split(':'))
            dt_ant_local = datetime(int(data_str[0:4]), int(data_str[5:7]), int(data_str[8:10]), h_ant, m_ant)
            dt_limite_anterior_utc = dt_ant_local + timedelta(hours=3)

        # Tentativas expansivas: 40min -> 90min -> 180min (ou até a janela máxima solicitada)
        janelas_para_testar = [janela_inicial_minutos]
        if janela_maxima_minutos > janela_inicial_minutos:
            if janela_inicial_minutos < 90 <= janela_maxima_minutos:
                janelas_para_testar.append(90)
            if janela_maxima_minutos not in janelas_para_testar:
                janelas_para_testar.append(janela_maxima_minutos)

        ponto_desembarque = None
        ponto_embarque = None
        janela_usada = janela_inicial_minutos

        for janela_atual in janelas_para_testar:
            janela_usada = janela_atual
            dt_inicio_janela = dt_desembarque_utc - timedelta(minutes=janela_atual)
            
            # Ajusta se a corrida anterior ocorreu depois do início da janela
            if dt_limite_anterior_utc and dt_limite_anterior_utc > dt_inicio_janela:
                dt_inicio_janela = dt_limite_anterior_utc

            dt_fim_janela = dt_desembarque_utc + timedelta(minutes=3)

            start_str = dt_inicio_janela.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_str = dt_fim_janela.strftime("%Y-%m-%dT%H:%M:%S.999Z")

            # Puxa os pontos de GPS ordenados do mais recente para o mais antigo (Regressão)
            pontos = await db.historico_gps.find({
                "motorista_id": motorista_id,
                "timestamp": {"$gte": start_str, "$lte": end_str}
            }).sort("timestamp", -1).to_list(length=1000)

            if not pontos:
                continue

            ponto_desembarque = None
            ponto_embarque = None

            for p in pontos:
                rua = p.get("rua", "")
                ts = p.get("timestamp")

                dt_utc = datetime.strptime(ts.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                dt_loc = dt_utc - timedelta(hours=3)
                hora_loc_str = dt_loc.strftime("%H:%M:%S")

                sim_origem = _calcular_similaridade_ruas(rua, origem_ocr)
                sim_destino = _calcular_similaridade_ruas(rua, destino_ocr)

                if not ponto_desembarque and sim_destino >= 0.3:
                    ponto_desembarque = {
                        "horario_local": hora_loc_str,
                        "rua": rua,
                        "timestamp": ts,
                        "coordenadas": p.get("localizacao", {}).get("coordinates")
                    }

                if ponto_desembarque and sim_origem >= 0.3:
                    ponto_embarque = {
                        "horario_local": hora_loc_str,
                        "rua": rua,
                        "timestamp": ts,
                        "coordenadas": p.get("localizacao", {}).get("coordinates")
                    }
                    break # Sucesso! Encontrou o embarque nesta janela.

            # Se encontrou ambos os pontos, não precisa testar janelas maiores (fallback concluído com sucesso)
            if ponto_embarque and ponto_desembarque:
                break

        if ponto_embarque and ponto_desembarque:
            dt_emb = datetime.strptime(ponto_embarque["horario_local"], "%H:%M:%S")
            dt_des = datetime.strptime(ponto_desembarque["horario_local"], "%H:%M:%S")
            duracao_min = round((dt_des - dt_emb).total_seconds() / 60.0, 1)

            return {
                "sucesso": True,
                "embarque": ponto_embarque,
                "desembarque": ponto_desembarque,
                "duracao_minutos": duracao_min,
                "janela_telemetria_usada_min": janela_usada
            }
        else:
            return {
                "sucesso": False,
                "motivo": f"Não foi possível parear a origem e destino mesmo expandindo a busca até {janela_usada} minutos.",
                "desembarque_parcial": ponto_desembarque
            }

    except Exception as e:
        return {
            "sucesso": False,
            "motivo": str(e)
        }

async def reconstruir_trajeto_uber(
    db: AsyncIOMotorDatabase,
    motorista_id: str,
    data_str: str,
    horario_embarque_str: str,
    origem_ocr: str,
    destino_ocr: str,
    janela_inicial_minutos: int = 40,
    janela_maxima_minutos: int = 180,
    horario_embarque_proximo_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Varre a telemetria em ordem PROGRESSIVA (do passado para o futuro),
    já que na UBER o horário capturado no extrato (ex: '08:30') refere-se ao EMBARQUE.
    
    Localiza o ponto de Embarque na hora de início e avança no tempo até 
    encontrar a chegada ao Destino (Desembarque).
    """
    try:
        if not horario_embarque_str or ':' not in horario_embarque_str:
            raise ValueError("Horário de embarque inválido")

        hora, minuto = map(int, horario_embarque_str.split(':'))
        dt_embarque_local = datetime(int(data_str[0:4]), int(data_str[5:7]), int(data_str[8:10]), hora, minuto)
        dt_embarque_utc = dt_embarque_local + timedelta(hours=3)

        # Limite superior se houver próxima corrida
        dt_limite_proximo_utc = None
        if horario_embarque_proximo_str and ':' in horario_embarque_proximo_str:
            h_prox, m_prox = map(int, horario_embarque_proximo_str.split(':'))
            dt_prox_local = datetime(int(data_str[0:4]), int(data_str[5:7]), int(data_str[8:10]), h_prox, m_prox)
            dt_limite_proximo_utc = dt_prox_local + timedelta(hours=3)

        janelas_para_testar = [janela_inicial_minutos]
        if janela_maxima_minutos > janela_inicial_minutos:
            if janela_inicial_minutos < 90 <= janela_maxima_minutos:
                janelas_para_testar.append(90)
            if janela_maxima_minutos not in janelas_para_testar:
                janelas_para_testar.append(janela_maxima_minutos)

        ponto_embarque = None
        ponto_desembarque = None
        janela_usada = janela_inicial_minutos

        for janela_atual in janelas_para_testar:
            janela_usada = janela_atual
            # Começa 3 minutos antes da hora do embarque e vai até a janela limite para a frente
            dt_inicio_janela = dt_embarque_utc - timedelta(minutes=3)
            dt_fim_janela = dt_embarque_utc + timedelta(minutes=janela_atual)

            if dt_limite_proximo_utc and dt_limite_proximo_utc < dt_fim_janela:
                dt_fim_janela = dt_limite_proximo_utc

            start_str = dt_inicio_janela.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_str = dt_fim_janela.strftime("%Y-%m-%dT%H:%M:%S.999Z")

            # Busca os pontos em ORDEM PROGRESSIVA (do mais antigo para o mais recente)
            pontos = await db.historico_gps.find({
                "motorista_id": motorista_id,
                "timestamp": {"$gte": start_str, "$lte": end_str}
            }).sort("timestamp", 1).to_list(length=1000)

            if not pontos:
                continue

            ponto_embarque = None
            ponto_desembarque = None

            for p in pontos:
                rua = p.get("rua", "")
                ts = p.get("timestamp")

                dt_utc = datetime.strptime(ts.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                dt_loc = dt_utc - timedelta(hours=3)
                hora_loc_str = dt_loc.strftime("%H:%M:%S")

                sim_origem = _calcular_similaridade_ruas(rua, origem_ocr)
                sim_destino = _calcular_similaridade_ruas(rua, destino_ocr)

                # 1. Encontra o Embarque primeiro
                if not ponto_embarque and sim_origem >= 0.3:
                    ponto_embarque = {
                        "horario_local": hora_loc_str,
                        "rua": rua,
                        "timestamp": ts,
                        "coordenadas": p.get("localizacao", {}).get("coordinates")
                    }

                # 2. Encontra o Desembarque após ter encontrado o embarque
                if ponto_embarque and sim_destino >= 0.3:
                    ponto_desembarque = {
                        "horario_local": hora_loc_str,
                        "rua": rua,
                        "timestamp": ts,
                        "coordenadas": p.get("localizacao", {}).get("coordinates")
                    }
                    break # Encontrou ambos!

            if ponto_embarque and ponto_desembarque:
                break

        if ponto_embarque and ponto_desembarque:
            dt_emb = datetime.strptime(ponto_embarque["horario_local"], "%H:%M:%S")
            dt_des = datetime.strptime(ponto_desembarque["horario_local"], "%H:%M:%S")
            duracao_min = round((dt_des - dt_emb).total_seconds() / 60.0, 1)

            return {
                "sucesso": True,
                "plataforma": "Uber",
                "embarque": ponto_embarque,
                "desembarque": ponto_desembarque,
                "duracao_minutos": duracao_min,
                "janela_telemetria_usada_min": janela_usada
            }
        else:
            return {
                "sucesso": False,
                "motivo": f"Não foi possível parear embarque e destino para Uber na janela de {janela_usada} minutos.",
                "embarque_parcial": ponto_embarque
            }

    except Exception as e:
        return {
            "sucesso": False,
            "motivo": str(e)
        }
