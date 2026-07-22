from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.database import get_database
from app.routers.auth import get_current_user

router = APIRouter(prefix="/config", tags=["configuracoes"])

DEFAULT_TEMPO_INATIVIDADE_MINUTOS = 25
DEFAULT_RAIO_MUDANCA_METROS = 30.0


class ConfigInatividadeSchema(BaseModel):
    tempo_inatividade_minutos: int = Field(default=25, ge=1, description="Tempo limite de inatividade em minutos")
    raio_mudanca_metros: float = Field(default=30.0, ge=1.0, description="Raio de mudança de posição em metros")


@router.get("/inatividade", response_model=ConfigInatividadeSchema)
async def get_config_inatividade():
    """
    Retorna as configurações atuais de inatividade (tempo em minutos e raio em metros).
    Retorna os valores padrão se ainda não houver alteração salva.
    """
    db = get_database()
    doc = await db["configuracoes"].find_one({"_id": "inatividade"})
    if not doc:
        return ConfigInatividadeSchema(
            tempo_inatividade_minutos=DEFAULT_TEMPO_INATIVIDADE_MINUTOS,
            raio_mudanca_metros=DEFAULT_RAIO_MUDANCA_METROS,
        )
    return ConfigInatividadeSchema(
        tempo_inatividade_minutos=doc.get("tempo_inatividade_minutos", DEFAULT_TEMPO_INATIVIDADE_MINUTOS),
        raio_mudanca_metros=float(doc.get("raio_mudanca_metros", DEFAULT_RAIO_MUDANCA_METROS)),
    )


@router.put("/inatividade", response_model=ConfigInatividadeSchema)
async def update_config_inatividade(
    payload: ConfigInatividadeSchema,
    current_user: dict = Depends(get_current_user),
):
    """
    Atualiza as configurações globais de inatividade. Apenas gestores ou admins têm permissão.
    """
    if current_user.get("role") not in ["ADMIN", "GESTOR"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores e gestores podem alterar as configurações.",
        )

    db = get_database()
    data = payload.model_dump()
    await db["configuracoes"].update_one(
        {"_id": "inatividade"},
        {"$set": data},
        upsert=True,
    )
    return payload
