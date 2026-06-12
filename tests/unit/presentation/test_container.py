import pytest

from purview_mcp.domain.exceptions import ConfigurationError
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.infrastructure.repositories.pg_catalog_repository import PgCatalogRepository
from purview_mcp.infrastructure.repositories.purview_catalog_repository import (
    PurviewCatalogRepository,
)
from purview_mcp.presentation.container import build_container


def test_purview_backend_uses_live_repos_and_no_db() -> None:
    container = build_container(Settings(purview_account_name="acct", serving_backend="purview"))
    assert container.db_engine is None
    assert container.db_sessionmaker is None
    assert container.scheduler is None
    assert isinstance(container.get_asset_details._catalog, PurviewCatalogRepository)


def test_postgres_backend_wires_db_and_scheduler() -> None:
    container = build_container(
        Settings(
            purview_account_name="acct",
            serving_backend="postgres",
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        )
    )
    assert container.db_engine is not None
    assert container.db_sessionmaker is not None
    assert container.scheduler is not None
    assert isinstance(container.get_asset_details._catalog, PgCatalogRepository)


def test_postgres_without_database_url_raises() -> None:
    # Fail fast: postgres serving requested but no DATABASE_URL configured.
    # __main__ turns this ConfigurationError into a clean exit(1).
    with pytest.raises(ConfigurationError):
        build_container(Settings(purview_account_name="acct", serving_backend="postgres"))


def test_unknown_serving_backend_raises() -> None:
    # A typo like "postgre" must fail fast, not silently serve live.
    with pytest.raises(ConfigurationError):
        build_container(Settings(purview_account_name="acct", serving_backend="postgre"))


def test_etl_disabled_keeps_db_without_scheduler() -> None:
    container = build_container(
        Settings(
            purview_account_name="acct",
            serving_backend="postgres",
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            etl_enabled=False,
        )
    )
    assert container.db_engine is not None
    assert container.scheduler is None


@pytest.mark.asyncio
async def test_container_aclose_disposes_engine() -> None:
    container = build_container(
        Settings(
            purview_account_name="acct",
            serving_backend="postgres",
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",
            etl_enabled=False,
        )
    )
    await container.aclose()  # should not raise even though no connection was opened
