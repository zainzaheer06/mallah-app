"""
Pytest fixtures.

We spin up an isolated test database per test session, run migrations,
and provide an httpx AsyncClient bound to the FastAPI app.

Tests use pytest-asyncio in 'auto' mode (configured in pyproject.toml).
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app


# Test DB URL strategy:
#   - If MALLAH_TEST_DATABASE_URL is set (CI), use it
#   - If main DATABASE_URL is Postgres, derive `_test` suffix
#   - Otherwise (local dev / SQLite), point at an in-memory SQLite
def _build_test_db_url() -> str:
    import os
    explicit = os.environ.get("MALLAH_TEST_DATABASE_URL")
    if explicit:
        return explicit
    url = settings.DATABASE_URL
    if "postgresql" in url and "/mallah" in url:
        return url.replace("/mallah", "/mallah_test")
    # Default: in-memory SQLite for fast local smoke testing
    return "sqlite+aiosqlite:///:memory:"


TEST_DATABASE_URL = _build_test_db_url()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(bind=test_engine, expire_on_commit=False)  # noqa: N806
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX client with the DB dependency overridden to use the test session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def api_prefix() -> str:
    return settings.API_V1_PREFIX
