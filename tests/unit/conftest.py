import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    yield