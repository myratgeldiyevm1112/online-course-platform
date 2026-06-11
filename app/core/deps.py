import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import raise_401, raise_403
from app.core.security import decode_token
from app.domain.entities.user import User, UserRole
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.db.session import get_db

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise_401("Invalid token")

    if payload.get("type") != "access":
        raise_401("Wrong token type")

    user_id = payload.get("sub")
    repo = SQLAlchemyUserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise_401("User not found")
    if not user.is_active:
        raise_401("Inactive user")
    return user


def require_role(*roles: UserRole):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise_403("Insufficient permissions")
        return current_user
    return checker