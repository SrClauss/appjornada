import base64
import json
import re
import urllib.request
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel

from app.core.config import settings
from app.routers.uploads import _salvar_arquivo

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

    modelos = ["gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
    
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
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                cleaned = re.sub(r"^```json\s*", "", raw_text.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()

                parsed = json.loads(cleaned)
                km_val = parsed.get("km")
                if km_val is not None:
                    try:
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


def _extrair_frames_video(video_bytes: bytes, max_frames: int = 6) -> list:
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
            for i in range(0, total_frames, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    # Redimensiona levemente se for muito grande para economizar payload
                    h, w = frame.shape[:2]
                    if w > 720:
                        new_w = 720
                        new_h = int(h * (720 / w))
                        frame = cv2.resize(frame, (new_w, new_h))
                    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    img_b64 = base64.b64encode(buffer).decode("utf-8")
                    frames_b64.append(img_b64)
                    if len(frames_b64) >= max_frames:
                        break
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
        "Responda EXCLUSIVAMENTE em formato JSON com a estrutura:\n"
        "{\n"
        '  "sucesso": true,\n'
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

    modelos = ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]
    for model in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
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
            print(f"[OCR Video] Erro no modelo {model}:", e)
            continue

    return {"sucesso": False, "mensagem": "Não foi possível processar o vídeo do extrato", "corridas": []}


@router.post("/extrato-video")
async def processar_extrato_video(
    file: UploadFile = File(...),
):
    video_bytes = await file.read()
    file.file.seek(0)
    video_url = await _salvar_arquivo(file, "extrato_video")

    frames = _extrair_frames_video(video_bytes, max_frames=6)
    if not frames:
        raise HTTPException(status_code=400, detail="Não foi possível extrair frames do vídeo enviado.")

    res_gemini = _chamar_gemini_extrato_video(frames)
    res_gemini["video_url"] = video_url
    return res_gemini

