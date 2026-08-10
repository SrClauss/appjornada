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


def _extrair_frames_video(video_bytes: bytes, max_frames: int = 8) -> list:
    import tempfile
    import os
    try:
        import cv2
    except ImportError:
        return []

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    frames_b64 = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            step = max(1, total_frames // max_frames)
            for i in range(max_frames):
                target = i * step
                cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                ret, frame = cap.read()
                if not ret:
                    break
                h, w = frame.shape[:2]
                if w > 720:
                    new_w = 720
                    new_h = int(h * (720 / w))
                    frame = cv2.resize(frame, (new_w, new_h))
                _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                img_b64 = base64.b64encode(buffer).decode("utf-8")
                frames_b64.append(img_b64)
        cap.release()
    except Exception as e:
        print("[OCR] Erro ao extrair frames do vídeo:", e)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return frames_b64


def _chamar_gemini_extrato_video(frames_b64_list: list) -> dict:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {"sucesso": False, "mensagem": "GEMINI_API_KEY não configurada", "corridas": []}

    prompt = (
        "Analise esta sequência de capturas de tela (frames) gravadas do histórico de corridas/ganhos de aplicativo de motorista (Uber / 99). "
        "Extraia a lista COMPLETA de corridas visíveis nas imagens, eliminando itens duplicados entre os frames. "
        "AVALIE TAMBÉM se os frames fornecidos foram suficientes para cobrir toda a rolagem de tela sem lacunas de imagens ou cortes entre uma corrida e outra. "
        "Responda EXCLUSIVAMENTE em formato JSON com a estrutura:\n"
        "{\n"
        '  "sucesso": true,\n'
        '  "historico_completo": true,\n'
        '  "necessita_mais_frames": false,\n'
        '  "total_corridas": 2,\n'
        '  "faturamento_total": 45.80,\n'
        '  "corridas": [\n'
        "    {\n"
        '      "horario": "11:18",\n'
        '      "plataforma": "Uber",\n'
        '      "categoria": "Comfort",\n'
        '      "valor_reais": 8.99,\n'
        '      "distancia_km": 2.93,\n'
        '      "duracao_min": 7.7,\n'
        '      "origem": "Praia do Canto, Vitória - ES",\n'
        '      "destino": "Jardim da Penha, Vitória - ES",\n'
        '      "cancelada": false\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    parts = [{"text": prompt}]
    for b64_img in frames_b64_list:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_img}})

    modelos = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for model in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
        
        for tentativa in range(3):
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode())
                    raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

                    parsed = json.loads(cleaned)
                    if isinstance(parsed, dict) and "corridas" in parsed:
                        parsed["sucesso"] = True
                        return parsed
            except Exception as e:
                print(f"[OCR Video] Erro na tentativa {tentativa+1} do modelo {model}:", e)
                if "503" in str(e) or "Service Unavailable" in str(e):
                    import time
                    time.sleep(2)
                    continue
                break

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
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado precisa ser uma imagem (JPEG/PNG).")

    img_bytes = await file.read()
    file.file.seek(0)

    foto_url = await _salvar_arquivo(file, "abastecimento")
    res_ai = _chamar_gemini_nota_fiscal(img_bytes, file.content_type)

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
):
    video_bytes = await file.read()
    file.file.seek(0)
    video_url = await _salvar_arquivo(file, "extrato_video")

    # 1ª tentativa: amostragem inicial leve com 6 frames
    max_f = 6
    frames = _extrair_frames_video(video_bytes, max_frames=max_f)
    if not frames:
        raise HTTPException(status_code=400, detail="Não foi possível extrair quadros do vídeo enviado.")

    res_gemini = _chamar_gemini_extrato_video(frames)

    # Re-amostragem adaptativa: se a IA indicar que faltam frames ou lacunas de imagem, refaz com amostragem mais densa (12 frames)
    if (res_gemini.get("necessita_mais_frames") is True or res_gemini.get("historico_completo") is False) and max_f < 12:
        print("[OCR Video] IA solicitou mais frames. Refazendo amostragem densa com 12 frames...")
        frames_densos = _extrair_frames_video(video_bytes, max_frames=12)
        if frames_densos:
            res_densos = _chamar_gemini_extrato_video(frames_densos)
            if res_densos.get("sucesso") and res_densos.get("corridas"):
                res_gemini = res_densos

    res_gemini["video_url"] = video_url
    return res_gemini
