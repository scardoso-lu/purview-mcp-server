"""Schema bootstrap for the Purview cache database.

The cache is a *derived, disposable* store — it can always be rebuilt from
Purview by re-running the ETL — so startup uses a fast, reliable bootstrap:
create the ``purview`` schema, enable the ``pg_trgm`` extension, then create any
missing tables/indexes from the ORM metadata.

Alembic (see ``alembic/`` + ``alembic.ini``) is wired to the same
``Base.metadata`` and is the source of truth for *versioned* schema evolution;
operators who want managed migrations run ``alembic upgrade head`` instead.
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from purview_mcp.infrastructure.db.models import SCHEMA, Base

logger = structlog.get_logger(__name__)


async def run_migrations(engine: AsyncEngine) -> None:
    """Ensure the schema, extensions, and tables exist."""
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("db.migrations.applied", schema=SCHEMA)
