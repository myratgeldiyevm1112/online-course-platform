import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthService
from app.core.deps import get_current_user
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    raise_400,
    raise_401,
)
from app.domain.entities.user import User
from app.infrastructure.db.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import get_redis

router = APIRouter(prefix="/auth", tags=["Auth"])


# --- Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


# --- Endpoints ---
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    service = AuthService(SQLAlchemyUserRepository(db), redis)
    try:
        return await service.register(body.email, body.password)
    except UserAlreadyExistsError as e:
        raise_400(e.message)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    service = AuthService(SQLAlchemyUserRepository(db), redis)
    try:
        return await service.login(body.email, body.password)
    except InvalidCredentialsError as e:
        raise_401(e.message)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    service = AuthService(SQLAlchemyUserRepository(db), redis)
    try:
        return await service.refresh(body.refresh_token)
    except InvalidTokenError as e:
        raise_401(e.message)


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    from app.infrastructure.db.session import async_session_factory
    service = AuthService(None, redis)
    await service.logout(current_user.id)