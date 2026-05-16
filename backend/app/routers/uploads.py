"""
Endpoint de upload de arquivos.

Salva arquivos em uploads/<contexto>/ e retorna a URL pública.
Em produção, troque _salvar_arquivo() por uma implementação S3/Firebase Storage.

Contextos aceitos:
  km_inicial | km_final | cnh | clrv | comprovante | sinistro | nota_fiscal | outros
"""
import os
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.staticfiles import StaticFiles

from app.core.dependencies import get_current_user
from app.models.user import UserPublic

CONTEXTOS_VALIDOS = {
    "km_inicial", "km_final", "cnh", "clrv",
    "comprovante", "sinistro", "nota_fiscal", "outros",
}

EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
TAMANHO_MAXIMO_MB = 10

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/app_jornada_uploads"))

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _resolver_dir(contexto: str) -> Path:
    pasta = UPLOAD_DIR / contexto
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


async def _salvar_arquivo(upload: UploadFile, contexto: str) -> str:
    """
    Salva o arquivo em disco e retorna a URL relativa.
    Substituir por upload para cloud em produção.
    """
    sufixo = Path(upload.filename or "arquivo").suffix.lower()
    if sufixo not in EXTENSOES_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extensão não permitida. Use: {', '.join(EXTENSOES_VALIDAS)}",
        )

    conteudo = await upload.read()
    tamanho_mb = len(conteudo) / (1024 * 1024)
    if tamanho_mb > TAMANHO_MAXIMO_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {TAMANHO_MAXIMO_MB} MB",
        )

    nome_arquivo = f"{uuid.uuid4().hex}{sufixo}"
    caminho = _resolver_dir(contexto) / nome_arquivo
    caminho.write_bytes(conteudo)

    return f"/static/uploads/{contexto}/{nome_arquivo}"


@router.post("/{contexto}", status_code=201)
async def fazer_upload(
    contexto: str,
    arquivo: UploadFile = File(...),
    _: UserPublic = Depends(get_current_user),
):
    """
    Envia um arquivo e recebe a URL para usar nos campos `*_url` das entidades.

    - **contexto**: categoria do arquivo (km_inicial, cnh, comprovante, etc.)
    - **arquivo**: o arquivo em multipart/form-data
    """
    if contexto not in CONTEXTOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contexto inválido. Use: {', '.join(sorted(CONTEXTOS_VALIDOS))}",
        )

    url = await _salvar_arquivo(arquivo, contexto)
    return {"url": url, "contexto": contexto}
