from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.db.database import get_db
from app.models.token import Token
from app.models.user import UserCreate, UserPublic
from app.services.auth_service import login, registrar_usuario
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def endpoint_login(
    form: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    return await login(db, email=form.username, senha=form.password)


@router.post("/registrar", response_model=UserPublic, status_code=201)
async def endpoint_registrar(dados: UserCreate, db=Depends(get_db)):
    return await registrar_usuario(db, dados)


@router.get("/me", response_model=UserPublic)
async def endpoint_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


@router.get("/setup-needed")
async def setup_needed(db=Depends(get_db)):
    """Retorna se o banco ainda não tem nenhum usuário (primeiro acesso)."""
    count = await db["users"].count_documents({})
    return {"setup_needed": count == 0}
