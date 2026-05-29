import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.db.database import get_db

router = APIRouter(prefix="/coleta", tags=["coleta"])

# Diretório base para arquivos raw — estrutura: coleta_snapshots/{package}/{data}/
COLETA_DIR = Path("coleta_snapshots")

# Chave simples para o app de coleta (sem necessidade de login do motorista)
# Defina COLETA_API_KEY no .env do servidor
COLETA_API_KEY = os.getenv("COLETA_API_KEY", "coleta-dev-key")

MAX_UPLOAD_MB = 20


def _verificar_api_key(x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != COLETA_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")


# ─── UPLOAD ──────────────────────────────────────────────────────────────────

@router.post("/upload", dependencies=[Depends(_verificar_api_key)])
async def receber_snapshot(
    arquivo: UploadFile = File(...),
    dispositivo: Optional[str] = None,   # ex: "Samsung A54 - Motorista João"
    db=Depends(get_db),
):
    """
    Recebe arquivo .jsonl do app Android.
    Cada linha = 1 snapshot: {timestamp, packageName, activityClass, elements[]}.
    
    Estratégia de gravação:
    1. Salva o arquivo raw em disco (backup fiel)
    2. Parseia cada linha e insere no MongoDB (para consulta/análise)
    """
    if not arquivo.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Formato esperado: .jsonl")

    conteudo = await arquivo.read()

    # Segurança: limita tamanho do upload
    if len(conteudo) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Arquivo excede {MAX_UPLOAD_MB}MB")

    linhas = [l.strip() for l in conteudo.decode("utf-8").splitlines() if l.strip()]
    if not linhas:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    # Detecta package pelo nome do arquivo (ex: com.taxis99_2026-05-29.jsonl)
    package = arquivo.filename.split("_")[0] if "_" in arquivo.filename else "desconhecido"
    hoje = datetime.now().strftime("%Y-%m-%d")
    ts_recebido = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── 1. Salvar arquivo raw em disco ────────────────────────────────────────
    pasta = COLETA_DIR / package / hoje
    pasta.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"{ts_recebido}_{dispositivo or 'sem-id'}_{arquivo.filename}"
    # Sanitiza nome do arquivo (evita path traversal)
    nome_arquivo = "".join(c for c in nome_arquivo if c.isalnum() or c in "._- ")
    caminho = pasta / nome_arquivo
    caminho.write_bytes(conteudo)

    # ── 2. Inserir cada snapshot no MongoDB ───────────────────────────────────
    documentos = []
    erros_parse = 0
    for linha in linhas:
        try:
            snap = json.loads(linha)
            snap["_recebido_em"] = ts_recebido
            snap["_dispositivo"] = dispositivo or "desconhecido"
            snap["_arquivo_origem"] = nome_arquivo
            documentos.append(snap)
        except json.JSONDecodeError:
            erros_parse += 1

    if documentos:
        await db["coleta_snapshots"].insert_many(documentos)

    return JSONResponse({
        "status": "ok",
        "arquivo_salvo": str(caminho),
        "telas_inseridas": len(documentos),
        "erros_parse": erros_parse,
    })


# ─── ANÁLISE ─────────────────────────────────────────────────────────────────

@router.get("/telas", dependencies=[Depends(_verificar_api_key)])
async def listar_telas_unicas(
    package: Optional[str] = None,
    db=Depends(get_db),
):
    """
    Retorna todas as activities/telas distintas capturadas.
    Útil para mapear quais telas o motorista passou durante o dia.
    """
    filtro = {}
    if package:
        filtro["packageName"] = package

    pipeline = [
        {"$match": filtro},
        {"$group": {
            "_id": {"package": "$packageName", "activity": "$activityClass"},
            "total_capturas": {"$sum": 1},
            "primeiro_visto": {"$min": "$timestamp"},
            "ultimo_visto": {"$max": "$timestamp"},
        }},
        {"$sort": {"total_capturas": -1}},
    ]

    resultado = await db["coleta_snapshots"].aggregate(pipeline).to_list(500)
    return [
        {
            "package": r["_id"]["package"],
            "activity": r["_id"]["activity"],
            "total_capturas": r["total_capturas"],
            "primeiro_visto": r["primeiro_visto"],
            "ultimo_visto": r["ultimo_visto"],
        }
        for r in resultado
    ]


@router.get("/telas/{activity_class}", dependencies=[Depends(_verificar_api_key)])
async def ver_snapshot_de_tela(
    activity_class: str,
    db=Depends(get_db),
):
    """
    Retorna um snapshot de exemplo de uma activity específica.
    Use para ver quais elementos/res-ids existem nessa tela.
    """
    snap = await db["coleta_snapshots"].find_one(
        {"activityClass": {"$regex": activity_class, "$options": "i"}},
        {"_id": 0},
    )
    if not snap:
        raise HTTPException(status_code=404, detail="Nenhum snapshot encontrado para essa activity")
    return snap


@router.get("/arquivos", dependencies=[Depends(_verificar_api_key)])
async def listar_arquivos():
    """Lista os arquivos raw recebidos no disco."""
    if not COLETA_DIR.exists():
        return []
    arquivos = []
    for f in sorted(COLETA_DIR.rglob("*.jsonl")):
        linhas = sum(1 for _ in f.open(encoding="utf-8"))
        arquivos.append({
            "caminho": str(f.relative_to(COLETA_DIR)),
            "telas": linhas,
            "tamanho_kb": round(f.stat().st_size / 1024, 1),
        })
    return arquivos
