from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decodificar_token
from app.db.database import get_db
from app.models.token import TokenData
from app.models.user import Role, User, UserPublic

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> UserPublic:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decodificar_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    role: str = payload.get("role")
    if user_id is None:
        raise credentials_exception

    token_data = TokenData(user_id=user_id, role=role)

    from bson import ObjectId
    doc = await db["users"].find_one({"_id": ObjectId(token_data.user_id)})
    if doc is None:
        raise credentials_exception

    return UserPublic(**doc)


def require_roles(*roles: Role):
    """Dependência de autorização por role. Uso: Depends(require_roles(Role.ADMIN))"""
    async def _check(current_user: UserPublic = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente",
            )
        return current_user
    return _check
