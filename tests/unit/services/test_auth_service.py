import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.auth_service import AuthService
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from app.core.security import hash_password
from app.domain.entities.user import User, UserRole


def make_user(**kwargs) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.STUDENT,
        is_active=True,
        is_verified=False,
        avatar_url=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return User(**defaults)


def make_service(existing_user=None, redis_stored=None):
    user_repo = AsyncMock()
    redis = AsyncMock()

    user_repo.get_by_email = AsyncMock(return_value=existing_user)
    user_repo.get_by_id = AsyncMock(return_value=existing_user)
    user_repo.create = AsyncMock(side_effect=lambda u: u)

    redis.get = AsyncMock(return_value=redis_stored)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)

    return AuthService(user_repo, redis), user_repo, redis


class TestRegister:
    async def test_success(self):
        service, _, redis = make_service(existing_user=None)
        result = await service.register("new@example.com", "password123")

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    async def test_duplicate_email_raises(self):
        service, _, _ = make_service(existing_user=make_user())

        with pytest.raises(UserAlreadyExistsError):
            await service.register("test@example.com", "password123")

    async def test_stores_refresh_token_in_redis(self):
        service, _, redis = make_service(existing_user=None)
        await service.register("new@example.com", "password123")

        redis.setex.assert_called_once()

    async def test_password_is_hashed(self):
        service, user_repo, _ = make_service(existing_user=None)
        await service.register("new@example.com", "password123")

        created_user = user_repo.create.call_args[0][0]
        assert created_user.hashed_password != "password123"


class TestLogin:
    async def test_success(self):
        user = make_user()
        service, _, _ = make_service(existing_user=user)
        result = await service.login("test@example.com", "password123")

        assert "access_token" in result
        assert "refresh_token" in result

    async def test_wrong_password_raises(self):
        user = make_user()
        service, _, _ = make_service(existing_user=user)

        with pytest.raises(InvalidCredentialsError):
            await service.login("test@example.com", "wrongpassword")

    async def test_user_not_found_raises(self):
        service, _, _ = make_service(existing_user=None)

        with pytest.raises(InvalidCredentialsError):
            await service.login("nobody@example.com", "password123")

    async def test_inactive_user_raises(self):
        user = make_user(is_active=False)
        service, _, _ = make_service(existing_user=user)

        with pytest.raises(InvalidCredentialsError):
            await service.login("test@example.com", "password123")

    async def test_issues_tokens_in_redis(self):
        user = make_user()
        service, _, redis = make_service(existing_user=user)
        await service.login("test@example.com", "password123")

        redis.setex.assert_called_once()


class TestRefresh:
    async def test_success(self):
        user = make_user()
        service, _, redis = make_service(existing_user=user)

        tokens = await service.login("test@example.com", "password123")
        refresh_token = tokens["refresh_token"]
        redis.get = AsyncMock(return_value=refresh_token)

        result = await service.refresh(refresh_token)
        assert "access_token" in result

    async def test_invalid_token_raises(self):
        service, _, _ = make_service()

        with pytest.raises(InvalidTokenError):
            await service.refresh("invalid.token.here")

    async def test_revoked_token_raises(self):
        user = make_user()
        service, _, redis = make_service(existing_user=user)

        tokens = await service.login("test@example.com", "password123")
        redis.get = AsyncMock(return_value="different_token")

        with pytest.raises(InvalidTokenError):
            await service.refresh(tokens["refresh_token"])


class TestLogout:
    async def test_deletes_redis_key(self):
        user = make_user()
        service, _, redis = make_service(existing_user=user)

        await service.logout(user.id)

        redis.delete.assert_called_once_with(f"refresh:{user.id}")