"""Integration tests — require a real Purview account.

These tests are skipped in CI unless PURVIEW_ACCOUNT_NAME is set in the environment.
Run locally with:
    PURVIEW_ACCOUNT_NAME=your-account uv run pytest tests/integration -v
"""

import os

import pytest

from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.infrastructure.repositories.purview_catalog_repository import (
    PurviewCatalogRepository,
)

PURVIEW_CONFIGURED = bool(os.getenv("PURVIEW_ACCOUNT_NAME"))

pytestmark = pytest.mark.skipif(
    not PURVIEW_CONFIGURED,
    reason="Integration tests require PURVIEW_ACCOUNT_NAME env var",
)


@pytest.fixture
def settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@pytest.fixture
def repo(settings: Settings) -> PurviewCatalogRepository:
    credential = PurviewCredentialProvider()
    client = DataMapClient(settings.purview_endpoint, credential)
    return PurviewCatalogRepository(client)


@pytest.mark.asyncio
async def test_search_returns_list(repo: PurviewCatalogRepository) -> None:
    results = await repo.search_assets("*", limit=5)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_result_fields_populated(repo: PurviewCatalogRepository) -> None:
    results = await repo.search_assets("*", limit=1)
    if results:
        asset = results[0]
        assert asset.id
        assert asset.name
        assert asset.asset_type
