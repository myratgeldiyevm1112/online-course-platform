import uuid
from datetime import timedelta

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.entities.user import User, UserRole
from app.domain.interfaces.user_repository import AbstractUserRepository


class AuthService:
    def __init__(
        self,
        user_repo: AbstractUserRepository,
        redis: aioredis.Redis,
    ):
        self.user_repo = user_repo
        self.redis = redis

    async def register(self, email: str, password: str) -> dict:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise UserAlreadyExistsError(f"User with email {email} already exists")

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.STUDENT,
            is_active=True,
            is_verified=False,
            avatar_url=None,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            updated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        created = await self.user_repo.create(user)
        return await self._issue_tokens(created)

    async def login(self, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("Account is disabled")
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise InvalidTokenError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Wrong token type")

        user_id = payload["sub"]
        stored = await self.redis.get(f"refresh:{user_id}")
        if stored != refresh_token:
            raise InvalidTokenError("Refresh token revoked or expired")

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise InvalidTokenError("User not found")

        return await self._issue_tokens(user)

    async def logout(self, user_id: uuid.UUID) -> None:
        await self.redis.delete(f"refresh:{user_id}")

    async def _issue_tokens(self, user: User) -> dict:
        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        ttl = int(timedelta(days=settings.jwt_refresh_token_expire_days).total_seconds())
        await self.redis.setex(f"refresh:{user.id}", ttl, refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }