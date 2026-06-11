"""Async SQLAlchemy engine / sessionmaker factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create the async engine for the Postgres cache database.

    ``database_url`` must use the asyncpg driver, e.g.
    ``postgresql+asyncpg://user:pass@host:5432/purview``.
    """
    return create_async_engine(database_url, pool_pre_ping=True, future=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
