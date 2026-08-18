from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.routers.auth import get_current_user

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


@router.get("/versao-app")
async def get_versao_app():
    """
    Retorna a versão mais recente do aplicativo mobile do motorista e o link de download direto do APK.
    """
    return {
        "versao_mais_recente": "1.0.8",
        "versao_minima": "1.0.0",
        "url_download": "http://2.24.121.189:3000/app-release.apk",
        "notas": "Versão com Microsoft Fluent Design 2, Métricas de Ticket Médio e Mapa de Calor."
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
    current_user: dict = Depends(get_current_user),
):
    """
    Atualiza as configurações globais de inatividade e limite de KM morta. Apenas gestores ou admins têm permissão.
    """
    if current_user.get("role") not in ["ADMIN", "GESTOR"]:
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

