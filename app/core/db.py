"""
Database engine and session management.

Uses async SQLAlchemy 2.x with asyncpg. Sessions are scoped per-request
via FastAPI dependency injection (see core.deps.get_db).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# --- Engine ---
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG and not settings.is_production,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # detect dropped connections
    pool_recycle=3600,   # recycle hourly to play nice with PgBouncer
)

# --- Session factory ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a transactional session.

    Commits on success, rolls back on exception, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
