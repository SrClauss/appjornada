import csv
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import Role

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


# ─── ADMIN (JWT Auth — painel de controle) ────────────────────────────────────

_admin_dep = Depends(require_roles(Role.ADMIN, Role.GESTOR))


@router.get("/admin/arquivos", dependencies=[_admin_dep])
async def admin_listar_arquivos():
    """Lista todos os arquivos raw no disco (para o painel de controle)."""
    if not COLETA_DIR.exists():
        return []
    arquivos = []
    for f in sorted(COLETA_DIR.rglob("*.jsonl"), reverse=True):
        rel = f.relative_to(COLETA_DIR)
        partes = rel.parts  # [package, data, nome_arquivo]
        arquivos.append({
            "caminho": str(rel),
            "package": partes[0] if len(partes) > 0 else "",
            "data": partes[1] if len(partes) > 1 else "",
            "nome": partes[-1],
            "telas": sum(1 for _ in f.open(encoding="utf-8")),
            "tamanho_kb": round(f.stat().st_size / 1024, 1),
            "modificado_em": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return arquivos


@router.get("/admin/telas", dependencies=[_admin_dep])
async def admin_listar_telas(
    package: Optional[str] = None,
    db=Depends(get_db),
):
    """Retorna telas únicas capturadas (via MongoDB), protegido por JWT."""
    filtro: dict = {}
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


@router.get("/admin/snapshots", dependencies=[_admin_dep])
async def admin_listar_snapshots(
    package: Optional[str] = None,
    activity: Optional[str] = None,
    dispositivo: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_db),
):
    """Lista snapshots individuais com filtros e paginação."""
    filtro: dict = {}
    if package:
        filtro["packageName"] = package
    if activity:
        filtro["activityClass"] = {"$regex": activity, "$options": "i"}
    if dispositivo:
        filtro["_dispositivo"] = {"$regex": dispositivo, "$options": "i"}

    cursor = db["coleta_snapshots"].find(filtro, {"_id": 0}).skip(skip).limit(limit)
    docs = await cursor.to_list(limit)
    total = await db["coleta_snapshots"].count_documents(filtro)
    return {"total": total, "skip": skip, "limit": limit, "items": docs}


@router.get("/admin/download/{caminho:path}", dependencies=[_admin_dep])
async def admin_download_arquivo(caminho: str):
    """Faz o download de um arquivo .jsonl raw pelo caminho relativo."""
    # Segurança: impede path traversal
    try:
        alvo = (COLETA_DIR / caminho).resolve()
        alvo.relative_to(COLETA_DIR.resolve())
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Caminho inválido")

    if not alvo.exists() or not alvo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    conteudo = alvo.read_bytes()
    return StreamingResponse(
        io.BytesIO(conteudo),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{alvo.name}"'},
    )


@router.get("/admin/export-csv", dependencies=[_admin_dep])
async def admin_exportar_csv(
    package: Optional[str] = None,
    activity: Optional[str] = None,
    limit: int = 1000,
    db=Depends(get_db),
):
    """Exporta snapshots como CSV para análise."""
    filtro: dict = {}
    if package:
        filtro["packageName"] = package
    if activity:
        filtro["activityClass"] = {"$regex": activity, "$options": "i"}

    cursor = db["coleta_snapshots"].find(filtro, {"_id": 0}).limit(limit)
    docs = await cursor.to_list(limit)

    if not docs:
        raise HTTPException(status_code=404, detail="Nenhum snapshot encontrado")

    # Coleta todas as chaves presentes
    colunas = list(dict.fromkeys(k for d in docs for k in d.keys()))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=colunas, extrasaction="ignore")
    writer.writeheader()
    for doc in docs:
        # Serializa campos complexos como JSON string
        row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in doc.items()}
        writer.writerow(row)

    output.seek(0)
    nome = f"coleta_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.delete("/admin/arquivo", dependencies=[_admin_dep])
async def admin_deletar_arquivo(caminho: str, db=Depends(get_db)):
    """Remove um arquivo .jsonl raw do disco e seus snapshots do MongoDB."""
    try:
        alvo = (COLETA_DIR / caminho).resolve()
        alvo.relative_to(COLETA_DIR.resolve())
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Caminho inválido")

    if not alvo.exists() or not alvo.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    nome_arquivo = alvo.name
    alvo.unlink()

    # Remove snapshots associados ao arquivo do MongoDB
    resultado = await db["coleta_snapshots"].delete_many({"_arquivo_origem": nome_arquivo})

    return {"status": "ok", "arquivo_removido": caminho, "snapshots_removidos": resultado.deleted_count}
