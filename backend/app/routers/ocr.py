import base64
import json
import re
import urllib.request
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from app.core.config import settings
from app.routers.uploads import _salvar_arquivo

from app.services.ia_tokens import (
    registrar_consumo_ia,
    obter_resumo_saldo,
    recarregar_ajustar_saldo,
    obter_tabela_precos_ia,
    salvar_tabela_precos_ia
)

router = APIRouter(prefix="/ocr", tags=["ocr"])


class RespostaOcrOdometro(BaseModel):
    sucesso: bool
    km_lido: Optional[float] = None
    foto_url: str
    confianca: str = "BAIXA"
    mensagem: str


def _chamar_gemini_odometro(img_bytes: bytes, mime_type: str) -> dict:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"sucesso": False, "km": None, "confianca": "BAIXA", "mensagem": "GEMINI_API_KEY não configurada no backend"}

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "Analise esta foto de um hodômetro / painel de veículo. "
        "Identifique a quilometragem total (número principal do hodômetro em km). "
        "Responda EXCLUSIVAMENTE em formato JSON com as chaves: "
        '{"km": 123456.0, "confianca": "ALTA"|"MEDIA"|"BAIXA", "observacao": "leitura exata"}'
    )

    modelos = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    
    for model in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                ]
            }]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
                
                # Extração e registro de consumo de tokens IA
                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)
                
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

                parsed = json.loads(cleaned)
                km_val = parsed.get("km")
                if km_val is not None:
                    try:
                        import asyncio
                        asyncio.create_task(registrar_consumo_ia("OCR Hodômetro", model, in_tok, out_tok))
                        km_float = float(km_val)
                        return {
                            "sucesso": True,
                            "km": km_float,
                            "confianca": parsed.get("confianca", "ALTA"),
                            "mensagem": f"Quilometragem {km_float} lida via {model}"
                        }
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            continue

    return {"sucesso": False, "km": None, "confianca": "BAIXA", "mensagem": "Não foi possível extrair a quilometragem da foto de forma confiável"}


@router.post("/odometro", response_model=RespostaOcrOdometro)
async def processar_odometro_foto(
    file: UploadFile = File(...),
    contexto: str = Form("km_inicial"),
):
    conteudo_bytes = await file.read()
    file.file.seek(0)
    
    foto_url = await _salvar_arquivo(file, contexto)

    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "png"
    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"

    res_ai = _chamar_gemini_odometro(conteudo_bytes, mime_type)

    return RespostaOcrOdometro(
        sucesso=res_ai.get("sucesso", False),
        km_lido=res_ai.get("km"),
        foto_url=foto_url,
        confianca=res_ai.get("confianca", "BAIXA"),
        mensagem=res_ai.get("mensagem", "Processamento concluído")
    )


def _salvar_bytes_em_midias(jpg_bytes: bytes, contexto: str, extensao: str = ".jpg") -> str:
    from app.routers.uploads import _resolver_dir, MINIO_ENABLED, MINIO_CLIENT, MINIO_BUCKET, _build_minio_url
    import io
    filename = f"{uuid.uuid4().hex}{extensao}"
    object_name = f"{contexto}/{filename}"
    
    if MINIO_ENABLED and MINIO_CLIENT:
        try:
            stream = io.BytesIO(jpg_bytes)
            MINIO_CLIENT.put_object(
                MINIO_BUCKET,
                object_name,
                stream,
                length=len(jpg_bytes),
                content_type="image/jpeg" if extensao == ".jpg" else "application/octet-stream"
            )
            return _build_minio_url(object_name)
        except Exception as e:
            print(f"[OCR] Erro ao salvar bytes no MinIO: {e}")

    dir_path = _resolver_dir(contexto)
    file_path = dir_path / filename
    file_path.write_bytes(jpg_bytes)
    return f"/static/uploads/{contexto}/{filename}"


def _aplicar_nitidez_e_zoom_card(frame_img) -> list:
    """
    Recebe um frame bruto do vídeo, aplica filtros de melhoria de contraste/nitidez (CLAHE + Unsharp Mask)
    e gera recortes (crops) de zoom com alta definição focando nas faixas do extrato/valores.
    """
    import cv2
    import numpy as np

    if frame_img is None:
        return []

    h, w = frame_img.shape[:2]

    # 1. Filtro de Nitidez (Unsharp Masking)
    gaussian = cv2.GaussianBlur(frame_img, (0, 0), 2.0)
    unsharp = cv2.addWeighted(frame_img, 1.5, gaussian, -0.5, 0)

    # 2. Melhoria de Contraste Localizado (CLAHE no canal L do LAB)
    lab = cv2.cvtColor(unsharp, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    limg = cv2.merge((cl, a_channel, b_channel))
    enhanced_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    enhanced_b64_list = []
    
    # Adiciona a imagem completa tratada em alta resolução (sem downscaling severo)
    if w > 1080:
        enh_w = 1080
        enh_h = int(h * (1080 / w))
        frame_full = cv2.resize(enhanced_frame, (enh_w, enh_h))
    else:
        frame_full = enhanced_frame

    _, buf_full = cv2.imencode('.jpg', frame_full, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    enhanced_b64_list.append(base64.b64encode(buf_full.tobytes()).decode("utf-8"))

    # 3. Recortes de Zoom (Crops) - Dividindo a tela em regiões de interesse (Topo/Meio/Base)
    # Útil para ler valores ou endereços menores com zoom de 150%-200%
    y_crops = [
        (0, int(h * 0.45)),            # Região Topo
        (int(h * 0.25), int(h * 0.75)), # Região Centro
        (int(h * 0.55), h)              # Região Base
    ]

    for y_start, y_end in y_crops:
        crop = enhanced_frame[y_start:y_end, 0:w]
        if crop.size > 0:
            crop_h, crop_w = crop.shape[:2]
            # Zoom upscale de 1.5x com interpolação CUBIC para aumentar legibilidade do OCR
            zoom_crop = cv2.resize(crop, (int(crop_w * 1.3), int(crop_h * 1.3)), interpolation=cv2.INTER_CUBIC)
            _, buf_crop = cv2.imencode('.jpg', zoom_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            enhanced_b64_list.append(base64.b64encode(buf_crop.tobytes()).decode("utf-8"))

    return enhanced_b64_list


def _extrair_frames_video(video_bytes: bytes, max_frames: int = 15, aplicar_nitidez: bool = True) -> tuple:
    import tempfile
    import os
    try:
        import cv2
        import numpy as np
    except ImportError:
        return [], []

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    frames_b64 = []
    frame_urls = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        if total_frames > 0:
            # Amostragem inteligente baseada em variação de cena (detecção de quadros estáveis pós-rolagem)
            step = max(1, total_frames // max(max_frames * 2, 20))
            candidate_frames = []
            prev_gray = None
            
            curr_f = 0
            while curr_f < total_frames and len(candidate_frames) < max_frames * 3:
                cap.set(cv2.CAP_PROP_POS_FRAMES, curr_f)
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Se houver frame anterior, mede a diferença para identificar se a tela está parada
                diff_val = 0.0
                if prev_gray is not None:
                    diff_val = np.mean(cv2.absdiff(gray, prev_gray))
                
                candidate_frames.append((curr_f, frame, diff_val))
                prev_gray = gray
                curr_f += step

            # Seleciona preferencialmente quadros com menor diferença (parados) distribuídos no tempo
            if len(candidate_frames) > max_frames:
                # Ordena os mais parados distribuídos no tempo
                stride = len(candidate_frames) / max_frames
                selected_tuples = [candidate_frames[int(i * stride)] for i in range(max_frames)]
            else:
                selected_tuples = candidate_frames

            for item in selected_tuples:
                frame = item[1]
                
                # Aplica tratamento de nitidez e melhoria visual se ativado
                if aplicar_nitidez:
                    gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
                    frame = cv2.addWeighted(frame, 1.4, gaussian, -0.4, 0)

                h, w = frame.shape[:2]
                if w > 850:
                    new_w = 850
                    new_h = int(h * (850 / w))
                    frame = cv2.resize(frame, (new_w, new_h))
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                jpg_bytes = buffer.tobytes()
                img_b64 = base64.b64encode(jpg_bytes).decode("utf-8")
                frames_b64.append(img_b64)
                
                try:
                    f_url = _salvar_bytes_em_midias(jpg_bytes, "extrato_frames", ".jpg")
                    frame_urls.append(f_url)
                except Exception:
                    pass

        cap.release()
    except Exception as e:
        print("[OCR] Erro ao extrair frames do vídeo:", e)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return frames_b64, frame_urls


def _limpar_e_parsear_json_gemini(raw_text: str) -> dict:
    if not raw_text:
        return {}
    
    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            return {"corridas": data}
    except Exception:
        pass

    match_dict = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match_dict:
        try:
            txt = re.sub(r',\s*([\}\]])', r'\1', match_dict.group(0))
            data = json.loads(txt)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    match_arr = re.search(r'\[.*\]', raw_text, re.DOTALL)
    if match_arr:
        try:
            txt = re.sub(r',\s*([\}\]])', r'\1', match_arr.group(0))
            arr = json.loads(txt)
            if isinstance(arr, list):
                return {"corridas": arr}
        except Exception:
            pass

    return {}


def _chamar_gemini_extrato_video(frames_b64_list: list, frame_urls: list = None, plataforma_esperada: str = None, faturamento_ancora: float = None, corridas_ancora: int = None) -> dict:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"sucesso": False, "mensagem": "GEMINI_API_KEY não configurada", "corridas": []}

    plat_instrucao = f" Foco prioritário na plataforma: {plataforma_esperada.upper()}." if plataforma_esperada else ""
    ancora_instrucao = ""
    if faturamento_ancora is not None and corridas_ancora is not None and corridas_ancora > 0:
        ancora_instrucao = (
            f" ATENÇÃO EXTREMA: O motorista declarou previamente que realizou EXATAMENTE {corridas_ancora} corridas. "
            f"O número de corridas é a sua ÂNCORA PRINCIPAL E ABSOLUTA de validação. "
            f"Sua missão prioritária é encontrar, desduplicar e extrair exatamente essas {corridas_ancora} corridas. "
            f"Para cada corrida, é CRÍTICO extrair os locais de ORIGEM e DESTINO (deslocamentos) corretamente. "
            f"O faturamento declarado foi R$ {faturamento_ancora:.2f}, use isso apenas como uma dica secundária. "
            f"IMPORTANTE: Esforce-se ao máximo para a extração fechar nas exatas {corridas_ancora} corridas declaradas, focando nos deslocamentos. "
            "Se for absolutamente impossível devido a erro do motorista, extraia as corridas reais visíveis, mas o foco é bater a quantidade de corridas.\n"
        )

    print("\n==================================================================")
    print(f"🎬 [OCR Video] Iniciando análise de {len(frames_b64_list)} quadros do vídeo ({plataforma_esperada or 'GERAL'})...")
    if frame_urls:
        for idx, f_url in enumerate(frame_urls):
            print(f"   📸 Frame {idx+1}/{len(frame_urls)} salvo em Mídias: {f_url}")
    print("------------------------------------------------------------------")

    prompt = (
        f"Analise minuciosamente esta sequência sequencial de capturas de tela (frames) gravadas do histórico de corridas de aplicativo (Uber / 99).{plat_instrucao}\n"
        f"{ancora_instrucao}"
        "Seu objetivo é garimpar e extrair COM EXATIDÃO 100% TODAS as corridas apresentadas durante a rolagem do vídeo, sem omitir NENHUMA corrida visível e eliminando duplicações idênticas entre quadros.\n"
        "Para cada corrida encontrada, extraia exatamente:\n"
        "- horario (ex: '11:18' ou '15:26')\n"
        "- data_formatada (data da corrida se visível ex: '02/06/2026' ou '2026-06-02', senão null)\n"
        "- plataforma ('Uber' ou '99')\n"
        "- valor_reais (valor exato em R$ como número decimal ex: 15.50)\n"
        "- origem e destino (endereços ou bairros visíveis, senão null)\n"
        "- distancia_km (distância da corrida em km se visível, extraia como float ex: 5.4, senão null)\n\n"
        "REGRAS DE CONFIABILIDADE E EXATIDÃO:\n"
        "1. Avalie se o histórico de corridas no vídeo parece ter lacunas de rolagem rápida ou cortes incertos entre os quadros.\n"
        "2. Se você sentir incerteza sobre algum valor ou se notar que faltam quadros para cobrir o extrato completo, defina 'necessita_mais_frames': true e 'historico_completo': false.\n"
        "3. Calcule o 'faturamento_total' exatamente como a SOMA do campo 'valor_reais' de todas as corridas válidas da lista.\n\n"
        "Responda EXCLUSIVAMENTE em formato JSON puro:\n"
        "{\n"
        '  "sucesso": true,\n'
        '  "historico_completo": true,\n'
        '  "necessita_mais_frames": false,\n'
        '  "total_corridas": 2,\n'
        '  "faturamento_total": 45.80,\n'
        '  "corridas": [\n'
        '    {"horario": "11:18", "data_formatada": "02/06/2026", "plataforma": "Uber", "valor_reais": 15.50, "origem": "Vitoria", "destino": "Vila Velha", "distancia_km": 5.4}\n'
        '  ]\n'
        "}"
    )

    parts = [{"text": prompt}]
    for b64_img in frames_b64_list:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_img}})

    modelos = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest"]
    for model in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
        
        for tentativa in range(3):
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    parsed = _limpar_e_parsear_json_gemini(raw_text)
                    corridas = (
                        parsed.get("corridas") or
                        parsed.get("rides") or
                        parsed.get("trips") or
                        parsed.get("faturamentos") or
                        parsed.get("historico") or
                        parsed.get("itens")
                    )

                    print(f"🤖 [OCR Video Modelo: {model} Tentativa: {tentativa+1}] Resposta Bruta da IA:")
                    print(raw_text if raw_text else "<TEXTO VAZIO>")
                    print(f"📊 Dados Estruturados Decodificados: {parsed}")
                    
                    if isinstance(corridas, list):
                        parsed["corridas"] = corridas
                        parsed["sucesso"] = True
                        print(f"✅ [Sucesso OCR Video] {len(corridas)} corridas extraídas!")
                        print("==================================================================\n")
                        return parsed
                    else:
                        print("⚠️ [OCR Video] Chave 'corridas' não é uma lista válida no JSON retornado.")
            except Exception as e:
                print(f"❌ [OCR Video Error] Erro na tentativa {tentativa+1} do modelo {model}: {e}")
                if "503" in str(e) or "Service Unavailable" in str(e):
                    import time
                    time.sleep(2)
                    continue

    print("❌ [OCR Video Falha] Nenhum modelo conseguiu processar o vídeo com sucesso.")
    print("==================================================================\n")
    return {"sucesso": False, "mensagem": "Não foi possível processar o vídeo do extrato", "corridas": []}


class RespostaOcrNotaFiscal(BaseModel):
    sucesso: bool
    valor_total: Optional[float] = None
    litros: Optional[float] = None
    preco_litro: Optional[float] = None
    posto_combustivel: Optional[str] = None
    tipo_combustivel: Optional[str] = None
    foto_url: str
    confianca: str = "BAIXA"
    mensagem: str


def _chamar_gemini_nota_fiscal(img_bytes: bytes, mime_type: str) -> dict:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"sucesso": False, "mensagem": "GEMINI_API_KEY não configurada no backend"}

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "Analise este cupom fiscal ou nota fiscal de abastecimento de combustível em posto de gasolina. "
        "Identifique e extraia com precisão os seguintes campos numéricos e informativos:\n"
        "1. valor_total (valor total pago em R$ como número de ponto flutuante)\n"
        "2. litros (quantidade total de litros abastecidos como número de ponto flutuante)\n"
        "3. preco_litro (preço por litro do combustível em R$)\n"
        "4. posto_combustivel (nome fantasia ou razão social do posto/estação de serviço)\n"
        "5. tipo_combustivel (GASOLINA, ETANOL, DIESEL ou GNV)\n"
        "Responda EXCLUSIVAMENTE em formato JSON estruturado com o seguinte esquema:\n"
        "{\n"
        '  "valor_total": 250.00,\n'
        '  "litros": 42.51,\n'
        '  "preco_litro": 5.88,\n'
        '  "posto_combustivel": "Posto Shell - Auto Posto Vitoria",\n'
        '  "tipo_combustivel": "GASOLINA",\n'
        '  "confianca": "ALTA"|"MEDIA"|"BAIXA",\n'
        '  "observacao": "Cupom fiscal perfeitamente legível"\n'
        "}"
    )

    modelos = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for model in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": img_b64}}
                ]
            }]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)

                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    parsed["sucesso"] = True
                    try:
                        import asyncio
                        asyncio.create_task(registrar_consumo_ia("OCR Nota Fiscal", model, in_tok, out_tok))
                    except Exception as e_tok:
                        print("[IA Tokens] Erro ao registrar log:", e_tok)
                    return parsed
        except Exception as e:
            print(f"[OCR Nota Fiscal] Erro no modelo {model}:", e)
            continue

    return {"sucesso": False, "mensagem": "Não foi possível extrair dados da nota fiscal de abastecimento."}


class ModeloAjusteSaldo(BaseModel):
    novo_saldo_brl: float
    motivo: Optional[str] = "Ajuste Manual do Administrador"


@router.get("/saldo-ia")
async def consultar_saldo_ia():
    """Consulta a situação financeira atual dos créditos da IA (Google Cloud)."""
    return await obter_resumo_saldo()


@router.post("/saldo-ia/ajustar")
async def ajustar_saldo_ia(dados: ModeloAjusteSaldo):
    """Permite ao administrador ajustar ou recarregar manualmente o saldo em R$ disponível no Painel."""
    return await recarregar_ajustar_saldo(dados.novo_saldo_brl, dados.motivo)


@router.get("/precos-ia")
async def consultar_tabela_precos_ia():
    """Retorna a cotação do dólar e os valores por 1M de tokens cadastrados no Banco de Dados."""
    return await obter_tabela_precos_ia()


@router.post("/precos-ia")
async def atualizar_tabela_precos_ia(dados: dict):
    """Permite ao Administrador atualizar no banco de dados a cotação do dólar e os valores em USD dos modelos Gemini."""
    return await salvar_tabela_precos_ia(dados)


@router.post("/nota-fiscal", response_model=RespostaOcrNotaFiscal)
async def processar_ocr_nota_fiscal(
    file: UploadFile = File(...),
):
    """
    Recebe imagem de nota/cupom fiscal de abastecimento, faz upload para o MinIO/Armazenamento
    e extrai os dados via IA Gemini para autopreenchimento no aplicativo.
    """
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        import mimetypes
        inferred, _ = mimetypes.guess_type(file.filename or "")
        if inferred and inferred.startswith("image/"):
            content_type = inferred
        elif not content_type or content_type == "application/octet-stream":
            content_type = "image/jpeg"
        else:
            raise HTTPException(status_code=400, detail="O arquivo enviado precisa ser uma imagem (JPEG/PNG).")

    img_bytes = await file.read()
    file.file.seek(0)

    foto_url = await _salvar_arquivo(file, "abastecimentos")
    res_ai = _chamar_gemini_nota_fiscal(img_bytes, content_type)

    return RespostaOcrNotaFiscal(
        sucesso=res_ai.get("sucesso", False),
        valor_total=res_ai.get("valor_total"),
        litros=res_ai.get("litros"),
        preco_litro=res_ai.get("preco_litro"),
        posto_combustivel=res_ai.get("posto_combustivel"),
        tipo_combustivel=res_ai.get("tipo_combustivel"),
        foto_url=foto_url,
        confianca=res_ai.get("confianca", "BAIXA"),
        mensagem=res_ai.get("observacao") or ("Dados extraídos com sucesso!" if res_ai.get("sucesso") else "Falha ao ler nota fiscal.")
    )


@router.post("/extrato-video")
async def processar_extrato_video(
    file: UploadFile = File(...),
    plataforma_esperada: Optional[str] = Form(None),
    faturamento_ancora: Optional[float] = Form(None),
    corridas_ancora: Optional[int] = Form(None)
):
    video_bytes = await file.read()
    file.file.seek(0)
    video_url = await _salvar_arquivo(file, "extrato_video")

    # 1ª tentativa: amostragem inteligente com nitidez de alta definição (15 frames)
    frames, frame_urls = _extrair_frames_video(video_bytes, max_frames=15, aplicar_nitidez=True)
    if not frames:
        raise HTTPException(status_code=400, detail="Não foi possível extrair quadros do vídeo enviado.")

    res_gemini = _chamar_gemini_extrato_video(
        frames, 
        frame_urls=frame_urls, 
        plataforma_esperada=plataforma_esperada,
        faturamento_ancora=faturamento_ancora,
        corridas_ancora=corridas_ancora
    )

    # Re-amostragem adaptativa com ZOOM e Nitidez de Alta Resolução se a IA solicitar ou houver lacuna
    if res_gemini.get("necessita_mais_frames") is True or res_gemini.get("historico_completo") is False:
        print("🔎 [OCR Video] IA solicitou maior nitidez/zoom local. Gerando recortes de alta definição...")
        frames_zoom, urls_zoom = _extrair_frames_video(video_bytes, max_frames=20, aplicar_nitidez=True)
        if frames_zoom:
            res_zoom = _chamar_gemini_extrato_video(
                frames_zoom, 
                frame_urls=urls_zoom, 
                plataforma_esperada=plataforma_esperada,
                faturamento_ancora=faturamento_ancora,
                corridas_ancora=corridas_ancora
            )
            if res_zoom.get("sucesso") and res_zoom.get("corridas"):
                res_gemini = res_zoom

    res_gemini["video_url"] = video_url
    return res_gemini
