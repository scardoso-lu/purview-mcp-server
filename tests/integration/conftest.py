"""Shared fixtures for Postgres-backed integration tests.

These require a real PostgreSQL (for ``tsvector`` / ``pg_trgm`` / ``ARRAY`` /
``JSONB``). The database is obtained from, in order:

1. ``PURVIEW_TEST_DATABASE_URL`` (an async SQLAlchemy URL), if set;
2. a disposable ``postgres:16`` container via testcontainers (needs Docker).

If neither is available the dependent tests are skipped.
"""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from purview_mcp.infrastructure.db.engine import create_engine, create_sessionmaker
from purview_mcp.infrastructure.db.migrations import run_migrations
from purview_mcp.infrastructure.db.models import SCHEMA, Base

_TABLES = [t.name for t in Base.metadata.sorted_tables]


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    env_url = os.environ.get("PURVIEW_TEST_DATABASE_URL")
    if env_url:
        yield env_url
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except Exception as exc:  # pragma: no cover - import guard
        pytest.skip(f"testcontainers not available: {exc}")

    container = None
    try:
        try:
            container = PostgresContainer("postgres:16", driver="asyncpg")
        except TypeError:
            container = PostgresContainer("postgres:16")
        container.start()
    except Exception as exc:  # Docker not available / image pull failed
        if container is not None:
            try:
                container.stop()
            except Exception:
                pass
        pytest.skip(f"could not start Postgres container: {exc}")

    try:
        url = container.get_connection_url()
        if "+asyncpg" not in url:
            url = url.replace("postgresql+psycopg2", "postgresql+asyncpg").replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        yield url
    finally:
        container.stop()


@pytest_asyncio.fixture
async def sessionmaker(database_url: str) -> AsyncIterator[async_sessionmaker]:
    engine = create_engine(database_url)
    await run_migrations(engine)
    sm = create_sessionmaker(engine)
    # Clean slate per test.
    async with engine.begin() as conn:
        for name in _TABLES:
            await conn.execute(text(f'TRUNCATE TABLE "{SCHEMA}"."{name}" RESTART IDENTITY CASCADE'))
    try:
        yield sm
    finally:
        await engine.dispose()
