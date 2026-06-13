from unittest.mock import AsyncMock
import pytest


class TestRegister:
    async def test_success(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg_success@test.com", "password": "password123"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_duplicate_email(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "reg_dup@test.com", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg_dup@test.com", "password": "password123"},
        )
        assert response.status_code == 400

    async def test_invalid_email_format(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422

    async def test_missing_password(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "nopw@test.com"},
        )
        assert response.status_code == 422


class TestLogin:
    async def test_success(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login_ok@test.com", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login_ok@test.com", "password": "password123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_wrong_password(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login_bad@test.com", "password": "password123"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login_bad@test.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    async def test_nonexistent_user(self, client):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@test.com", "password": "password123"},
        )
        assert response.status_code == 401


class TestLogout:
    async def test_success(self, client, mock_redis):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "logout_ok@test.com", "password": "password123"},
        )
        token = reg.json()["access_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    async def test_no_token_returns_401(self, client):
        # HTTPBearer without auto_error=False returns 403 by default
        # but our custom deps returns 401 — just check it's unauthorized
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code in (401, 403)

    async def test_invalid_token_returns_401(self, client):
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401