"""
Endpoint de upload de arquivos.

Salva arquivos em MinIO quando configurado ou em uploads/<contexto>/ localmente. Retorna a URL pública.

Contextos aceitos:
  km_inicial | km_final | cnh | clrv | comprovante | sinistro | nota_fiscal | outros
"""
import io
import json
import os
import uuid
from pathlib import Path
from typing import Literal

from minio import Minio
from minio.error import S3Error
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from app.core.config import settings

from app.core.dependencies import get_current_user
from app.models.user import UserPublic

CONTEXTOS_VALIDOS = {
    "km_inicial", "km_final", "cnh", "clrv", "veiculo",
    "comprovante", "sinistro", "nota_fiscal", "outros", "vistoria",
}

EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
TAMANHO_MAXIMO_MB = 10

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/app_jornada_uploads"))

MINIO_ENABLED = bool(settings.MINIO_ENDPOINT and settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY)
MINIO_CLIENT = (
    Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    if MINIO_ENABLED
    else None
)
MINIO_BUCKET = settings.MINIO_BUCKET

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _resolver_dir(contexto: str) -> Path:
    pasta = UPLOAD_DIR / contexto
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _ensure_minio_bucket() -> None:
    if MINIO_CLIENT is None:
        return

    try:
        if not MINIO_CLIENT.bucket_exists(MINIO_BUCKET):
            MINIO_CLIENT.make_bucket(MINIO_BUCKET)
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{MINIO_BUCKET}/*"],
                    }
                ],
            }
            MINIO_CLIENT.set_bucket_policy(MINIO_BUCKET, json.dumps(policy))
    except S3Error:
        pass


def _build_minio_url(object_name: str) -> str:
    return f"/{MINIO_BUCKET}/{object_name}"


async def _upload_to_minio(upload: UploadFile, contexto: str, conteudo: bytes) -> str:
    if MINIO_CLIENT is None:
        raise RuntimeError("MinIO não está configurado")

    sufixo = Path(upload.filename or "arquivo").suffix.lower()
    object_name = f"{contexto}/{uuid.uuid4().hex}{sufixo}"
    stream = io.BytesIO(conteudo)
    stream.seek(0)
    _ensure_minio_bucket()
    MINIO_CLIENT.put_object(
        MINIO_BUCKET,
        object_name,
        stream,
        len(conteudo),
        content_type=upload.content_type or "application/octet-stream",
    )
    return _build_minio_url(object_name)


async def _salvar_arquivo(upload: UploadFile, contexto: str) -> str:
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

    if MINIO_ENABLED:
        try:
            return await _upload_to_minio(upload, contexto, conteudo)
        except Exception:
            pass

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
    if contexto not in CONTEXTOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contexto inválido. Use: {', '.join(sorted(CONTEXTOS_VALIDOS))}",
        )

    url = await _salvar_arquivo(arquivo, contexto)
    return {"url": url, "contexto": contexto}
