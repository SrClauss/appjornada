import io
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.routers.uploads import MINIO_CLIENT, MINIO_BUCKET, _ensure_minio_bucket

router = APIRouter(prefix="/config", tags=["configuracoes"])

DEFAULT_TEMPO_INATIVIDADE_MINUTOS = 25
DEFAULT_RAIO_MUDANCA_METROS = 30.0
DEFAULT_LIMITE_KM_MORTA_PCT = 20.0
DEFAULT_TEMPO_MAXIMO_ABASTECIMENTO_MINUTOS = 30


class ConfigInatividadeSchema(BaseModel):
    tempo_inatividade_minutos: int = Field(default=25, ge=1, description="Tempo limite de inatividade em minutos")
    raio_mudanca_metros: float = Field(default=30.0, ge=1.0, description="Raio de mudança de posição em metros")
    limite_km_morta_pct: float = Field(default=20.0, ge=0.0, le=100.0, description="Limite máximo aceitável de Razão KM Morta (%) pelo Gestor")
    tempo_maximo_abastecimento_minutos: int = Field(default=30, ge=1, description="Tempo máximo de parada para abastecimento em minutos")


class BaseOperacaoSchema(BaseModel):
    id: Optional[str] = None
    nome: str = Field(..., description="Nome da base de operações (ex: Base São Mateus)")
    cidade: Optional[str] = None
    estado: Optional[str] = None
    lat: float = Field(..., description="Latitude da base de operações")
    lon: float = Field(..., description="Longitude da base de operações")
    zoom_padrao: int = Field(default=13, ge=1, le=20, description="Nível de zoom padrão no mapa")
    is_principal: bool = Field(default=False, description="Indica se é a base principal de centralização da frota")


HISTORICO_VERSOES_APK = [
    {
        "versao": "1.2.4+17",
        "nome_versao": "1.2.4",
        "build_number": 17,
        "data_release": "2026-09-03",
        "tamanho_mb": "54.6 MB",
        "is_latest": True,
        "url_download": "/config/apk/download",
        "url_download_direto": "/config/apk/download",
        "resumo": "Versão de produção gerenciada dinamicamente no MinIO e MongoDB.",
        "alteracoes": [
            {"tipo": "FEATURE", "descricao": "Gerenciamento dinâmico do APK no MinIO com sincronização direta no MongoDB."},
            {"tipo": "FIX", "descricao": "Correção no roteamento de jornadas pendentes de auditoria."}
        ]
    }
]


@router.get("/apk")
async def get_config_apk():
    """
    Retorna os metadados do APK ativo cadastrado no MongoDB ('configuracoes' -> '_id': 'config_apk').
    """
    db = get_db()
    doc = await db["configuracoes"].find_one({"_id": "config_apk"})
    if not doc:
        return {
            "_id": "config_apk",
            "versao": "1.2.4",
            "build_number": 17,
            "versao_completa": "1.2.4+17",
            "nome_arquivo": "app-jornada-v1.2.4.apk",
            "tamanho_mb": "54.6 MB",
            "minio_object_name": "apk/app-jornada-v1.2.4.apk",
            "url_download": "/config/apk/download",
            "updated_at": datetime.utcnow().isoformat()
        }
    doc.pop("_id", None)
    return doc


@router.get("/apk/download")
@router.head("/apk/download")
async def download_apk():
    """
    Realiza o download direto do APK ativo armazenado no MinIO.
    Garante que apenas a versão corrente registrada no MongoDB/MinIO seja servida.
    """
    db = get_db()
    doc = await db["configuracoes"].find_one({"_id": "config_apk"})

    versao = doc.get("versao", "1.2.4") if doc else "1.2.4"
    filename = doc.get("nome_arquivo", f"app-jornada-v{versao}.apk") if doc else f"app-jornada-v{versao}.apk"
    object_name = doc.get("minio_object_name", f"apk/{filename}") if doc else f"apk/app-jornada-v{versao}.apk"

    if MINIO_CLIENT:
        try:
            _ensure_minio_bucket()
            objects = list(MINIO_CLIENT.list_objects(MINIO_BUCKET, prefix="apk/"))
            target_object = object_name
            if not any(o.object_name == object_name for o in objects) and objects:
                target_object = objects[0].object_name

            response = MINIO_CLIENT.get_object(MINIO_BUCKET, target_object)

            def iterfile():
                try:
                    for chunk in response.stream(32 * 1024):
                        yield chunk
                finally:
                    response.close()
                    response.release_conn()

            return StreamingResponse(
                iterfile(),
                media_type="application/vnd.android.package-archive",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache"
                }
            )
        except Exception as e:
            print(f"[config_sistema] Erro ao obter APK do MinIO: {e}")

    # Fallback local
    local_paths = [
        Path(f"/tmp/app_jornada_uploads/{object_name}"),
        Path(f"/usr/share/nginx/html/{filename}"),
        Path(f"/usr/share/nginx/html/app-release.apk"),
    ]
    for p in local_paths:
        if p.exists():
            return FileResponse(
                path=str(p),
                filename=filename,
                media_type="application/vnd.android.package-archive",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache"
                }
            )

    raise HTTPException(status_code=404, detail="APK não encontrado no MinIO nem no servidor local.")


@router.post("/apk/upload")
async def upload_apk(
    file: UploadFile = File(...),
    versao: Optional[str] = Form(None),
    build_number: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload manual de um novo APK via API. Remove versões anteriores no MinIO e atualiza o MongoDB.
    """
    user_role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)
    if user_role not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem enviar novas versões do APK."
        )

    conteudo = await file.read()
    tamanho_mb = len(conteudo) / (1024 * 1024)

    if not versao:
        m = re.search(r"v?(\d+\.\d+\.\d+)", file.filename or "")
        versao = m.group(1) if m else "1.2.4"
    if not build_number:
        build_number = 17

    target_filename = f"app-jornada-v{versao}.apk"
    object_name = f"apk/{target_filename}"

    if MINIO_CLIENT:
        _ensure_minio_bucket()
        try:
            old_objs = list(MINIO_CLIENT.list_objects(MINIO_BUCKET, prefix="apk/"))
            for o in old_objs:
                MINIO_CLIENT.remove_object(MINIO_BUCKET, o.object_name)
        except Exception as e:
            print(f"[config_sistema] Erro ao deletar APKs antigos do MinIO: {e}")

        stream = io.BytesIO(conteudo)
        MINIO_CLIENT.put_object(
            MINIO_BUCKET,
            object_name,
            stream,
            len(conteudo),
            content_type="application/vnd.android.package-archive"
        )

    db = get_db()
    config_apk = {
        "_id": "config_apk",
        "versao": versao,
        "build_number": build_number,
        "versao_completa": f"{versao}+{build_number}",
        "nome_arquivo": target_filename,
        "tamanho_mb": f"{tamanho_mb:.1f} MB",
        "minio_object_name": object_name,
        "url_download": "/config/apk/download",
        "minio_url": f"/{MINIO_BUCKET}/{object_name}",
        "updated_at": datetime.utcnow().isoformat()
    }

    await db["configuracoes"].update_one(
        {"_id": "config_apk"},
        {"$set": config_apk},
        upsert=True
    )
    return config_apk


@router.get("/versao-app")
async def get_versao_app():
    """
    Retorna a versão mais recente do aplicativo mobile do motorista e o link de download direto do MinIO/API.
    """
    db = get_db()
    doc = await db["configuracoes"].find_one({"_id": "config_apk"})
    if doc:
        return {
            "versao_mais_recente": doc.get("versao", "1.2.4"),
            "versao_completa": doc.get("versao_completa", "1.2.4+17"),
            "versao_minima": "1.0.0",
            "url_download": doc.get("url_download", "/config/apk/download"),
            "url_download_direto": doc.get("url_download", "/config/apk/download"),
            "tamanho_mb": doc.get("tamanho_mb", "54.6 MB"),
            "notas": "Versão mais recente mantida no MinIO e MongoDB."
        }

    latest = HISTORICO_VERSOES_APK[0]
    return {
        "versao_mais_recente": latest["nome_versao"],
        "versao_completa": latest["versao"],
        "versao_minima": "1.0.0",
        "url_download": "/config/apk/download",
        "url_download_direto": "/config/apk/download",
        "notas": latest["resumo"]
    }


@router.get("/versao-app/historico")
async def get_historico_versoes_app():
    """
    Retorna a lista de versões mantendo a versão ativa no MinIO em 1º lugar.
    """
    db = get_db()
    doc = await db["configuracoes"].find_one({"_id": "config_apk"})

    list_versoes = list(HISTORICO_VERSOES_APK)
    if doc:
        v_ativa = {
            "versao": doc.get("versao_completa", "1.2.4+17"),
            "nome_versao": doc.get("versao", "1.2.4"),
            "build_number": doc.get("build_number", 17),
            "data_release": (doc.get("updated_at") or "")[:10] or "2026-09-03",
            "tamanho_mb": doc.get("tamanho_mb", "54.6 MB"),
            "is_latest": True,
            "url_download": doc.get("url_download", "/config/apk/download"),
            "url_download_direto": doc.get("url_download", "/config/apk/download"),
            "resumo": "Versão ativa no servidor armazenada no MinIO e registrada no MongoDB.",
            "alteracoes": [
                {"tipo": "RELEASE", "descricao": f"APK v{doc.get('versao')} ativo no MinIO e MongoDB."}
            ]
        }
        list_versoes = [v_ativa] + [v for v in HISTORICO_VERSOES_APK if v["nome_versao"] != doc.get("versao")]

    return {
        "versoes": list_versoes,
        "total": len(list_versoes)
    }



@router.get("/inatividade", response_model=ConfigInatividadeSchema)
async def get_config_inatividade():
    """
    Retorna as configurações atuais de inatividade e auditoria de KM morta.
    Retorna os valores padrão se ainda não houver alteração salva.
    """
    db = get_db()
    doc = await db["configuracoes"].find_one({"_id": "inatividade"})
    if not doc:
        return ConfigInatividadeSchema(
            tempo_inatividade_minutos=DEFAULT_TEMPO_INATIVIDADE_MINUTOS,
            raio_mudanca_metros=DEFAULT_RAIO_MUDANCA_METROS,
            limite_km_morta_pct=DEFAULT_LIMITE_KM_MORTA_PCT,
            tempo_maximo_abastecimento_minutos=DEFAULT_TEMPO_MAXIMO_ABASTECIMENTO_MINUTOS,
        )
    return ConfigInatividadeSchema(
        tempo_inatividade_minutos=doc.get("tempo_inatividade_minutos", DEFAULT_TEMPO_INATIVIDADE_MINUTOS),
        raio_mudanca_metros=float(doc.get("raio_mudanca_metros", DEFAULT_RAIO_MUDANCA_METROS)),
        limite_km_morta_pct=float(doc.get("limite_km_morta_pct", DEFAULT_LIMITE_KM_MORTA_PCT)),
        tempo_maximo_abastecimento_minutos=int(doc.get("tempo_maximo_abastecimento_minutos", DEFAULT_TEMPO_MAXIMO_ABASTECIMENTO_MINUTOS)),
    )


@router.put("/inatividade", response_model=ConfigInatividadeSchema)
async def update_config_inatividade(
    payload: ConfigInatividadeSchema,
    current_user=Depends(get_current_user),
):
    """
    Atualiza as configurações globais de inatividade e limite de KM morta. Apenas gestores ou admins têm permissão.
    """
    user_role = getattr(current_user, "role", None) if not isinstance(current_user, dict) else current_user.get("role")
    if user_role not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem alterar as configurações.",
        )

    db = get_db()
    data = payload.model_dump()
    await db["configuracoes"].update_one(
        {"_id": "inatividade"},
        {"$set": data},
        upsert=True,
    )
    return payload


# ─── BASES DE OPERAÇÕES ───────────────────────────────────────────────────────

@router.get("/bases", response_model=List[BaseOperacaoSchema])
async def listar_bases_operacoes():
    """
    Retorna a lista de bases de operações cadastradas.
    Se nenhuma base existir, cria automaticamente a base padrão inicial em São Mateus.
    """
    db = get_db()
    docs = await db["bases_operacoes"].find().to_list(100)
    if not docs:
        initial_doc = {
            "_id": "base_vitoria_serra",
            "nome": "Base Operacional Vitória/Serra",
            "cidade": "Serra",
            "estado": "ES",
            "lat": -20.26548,
            "lon": -40.29589,
            "zoom_padrao": 13,
            "is_principal": True,
        }
        await db["bases_operacoes"].insert_one(initial_doc)
        docs = [initial_doc]

    res = []
    for d in docs:
        d_copy = dict(d)
        d_copy["id"] = str(d_copy.pop("_id", ""))
        res.append(BaseOperacaoSchema(**d_copy))
    return res


@router.post("/bases", response_model=BaseOperacaoSchema, status_code=201)
async def criar_base_operacao(
    payload: BaseOperacaoSchema,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem cadastrar bases de operações.",
        )

    db = get_db()
    data = payload.model_dump()
    base_id = data.get("id") or f"base_{uuid4().hex[:8]}"
    data["_id"] = base_id
    if "id" in data:
        del data["id"]

    if payload.is_principal:
        await db["bases_operacoes"].update_many({}, {"$set": {"is_principal": False}})

    await db["bases_operacoes"].insert_one(data)
    data["id"] = base_id
    return BaseOperacaoSchema(**data)


@router.put("/bases/{base_id}", response_model=BaseOperacaoSchema)
async def atualizar_base_operacao(
    base_id: str,
    payload: BaseOperacaoSchema,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem alterar bases de operações.",
        )

    db = get_db()
    data = payload.model_dump()
    if "id" in data:
        del data["id"]

    if payload.is_principal:
        await db["bases_operacoes"].update_many({"_id": {"$ne": base_id}}, {"$set": {"is_principal": False}})

    resultado = await db["bases_operacoes"].update_one({"_id": base_id}, {"$set": data})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Base de operações não encontrada.")

    data["id"] = base_id
    return BaseOperacaoSchema(**data)


@router.delete("/bases/{base_id}", status_code=204)
async def deletar_base_operacao(
    base_id: str,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem excluir bases de operações.",
        )

    db = get_db()
    await db["bases_operacoes"].delete_one({"_id": base_id})

