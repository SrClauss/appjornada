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
