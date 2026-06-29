from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from datetime import time
from app.db.database import get_db
from app.models.preco_particular import PrecoParticular
from app.models.user import Role, UserPublic
from app.routers.auth import get_current_user

router = APIRouter(prefix="/config/precos-particulares", tags=["precos-particulares"])

def obter_intervalos_minutos(hora_inicio: str, hora_fim: str) -> List[tuple]:
    try:
        hi = time.fromisoformat(hora_inicio)
        hf = time.fromisoformat(hora_fim)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Formato de hora inválido. Use HH:MM ou HH:MM:SS"
        )
    start_min = hi.hour * 60 + hi.minute
    end_min = hf.hour * 60 + hf.minute
    if start_min <= end_min:
        return [(start_min, end_min)]
    else:
        return [(start_min, 1439), (0, end_min)]

def verificar_sobreposicao(hora_inicio_a: str, hora_fim_a: str, hora_inicio_b: str, hora_fim_b: str) -> bool:
    intervals_a = obter_intervalos_minutos(hora_inicio_a, hora_fim_a)
    intervals_b = obter_intervalos_minutos(hora_inicio_b, hora_fim_b)
    for sa, ea in intervals_a:
        for sb, eb in intervals_b:
            if max(sa, sb) < min(ea, eb):
                return True
    return False

@router.get("", response_model=List[PrecoParticular])
async def listar_precos_particulares(
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    docs = await db["precos_particulares"].find().to_list(None)
    for d in docs:
        d["_id"] = str(d["_id"])
    return [PrecoParticular(**d) for d in docs]

@router.post("", response_model=PrecoParticular, status_code=201)
async def criar_preco_particular(
    dados: PrecoParticular,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role not in (Role.ADMIN, Role.GESTOR):
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Validar que a nova faixa não sobrepõe nenhuma faixa existente
    existentes = await db["precos_particulares"].find().to_list(None)
    for ex in existentes:
        if verificar_sobreposicao(dados.hora_inicio, dados.hora_fim, ex["hora_inicio"], ex["hora_fim"]):
            raise HTTPException(
                status_code=400,
                detail=f"Esta faixa de horário conflita/sobrepõe com a faixa existente '{ex['nome']}' ({ex['hora_inicio']} até {ex['hora_fim']})."
            )

    doc = dados.model_dump(by_alias=True, exclude_none=True)
    if "_id" in doc:
        del doc["_id"]

    res = await db["precos_particulares"].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return PrecoParticular(**doc)

@router.put("/{id}", response_model=PrecoParticular)
async def atualizar_preco_particular(
    id: str,
    dados: PrecoParticular,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role not in (Role.ADMIN, Role.GESTOR):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID inválido")

    # Validar sobreposição ignorando a própria faixa que está sendo editada
    existentes = await db["precos_particulares"].find({"_id": {"$ne": ObjectId(id)}}).to_list(None)
    for ex in existentes:
        if verificar_sobreposicao(dados.hora_inicio, dados.hora_fim, ex["hora_inicio"], ex["hora_fim"]):
            raise HTTPException(
                status_code=400,
                detail=f"Esta faixa de horário conflita/sobrepõe com a faixa existente '{ex['nome']}' ({ex['hora_inicio']} até {ex['hora_fim']})."
            )

    doc = dados.model_dump(by_alias=True, exclude_none=True)
    if "_id" in doc:
        del doc["_id"]

    res = await db["precos_particulares"].update_one(
        {"_id": ObjectId(id)},
        {"$set": doc}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Faixa de preço não encontrada")

    doc["_id"] = id
    return PrecoParticular(**doc)

@router.delete("/{id}", status_code=204)
async def deletar_preco_particular(
    id: str,
    db=Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    if current_user.role not in (Role.ADMIN, Role.GESTOR):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="ID inválido")

    res = await db["precos_particulares"].delete_one({"_id": ObjectId(id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Faixa de preço não encontrada")
    return None
