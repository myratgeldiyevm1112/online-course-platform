import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock

from app.main import app
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import user as _user_models  # noqa: F401
from app.infrastructure.db.models import course as _course_models  # noqa: F401
from app.infrastructure.db.session import get_db
from app.infrastructure.redis.client import get_redis

TEST_DB_URL = "postgresql+asyncpg://course_user:course_pass@localhost:5432/course_test_db"

test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="function")
async def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, mock_redis: AsyncMock):
    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def instructor_token(client: AsyncClient) -> str:
    uid = uuid.uuid4().hex[:8]
    email = f"instructor_{uid}@test.com"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    await client.post(
        "/api/v1/users/me/instructor-apply",
        headers={"Authorization": f"Bearer {(await client.post('/api/v1/auth/login', json={'email': email, 'password': 'password123'})).json()['access_token']}"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return login.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def instructor_client(client: AsyncClient, instructor_token: str) -> AsyncClient:
    client.headers.update({"Authorization": f"Bearer {instructor_token}"})
    return client


@pytest_asyncio.fixture(scope="function")
async def student_token(client: AsyncClient) -> str:
    uid = uuid.uuid4().hex[:8]
    email = f"student_{uid}@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    return reg.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def student_client(client: AsyncClient, student_token: str) -> AsyncClient:
    client.headers.update({"Authorization": f"Bearer {student_token}"})
    return client