import pytest
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.repositories.purview_catalog_repository import (
    PurviewCatalogRepository,
    _parse_search_result,
)


def test_parse_search_result_maps_fields() -> None:
    hit = {
        "id": "test-guid",
        "name": "Orders Table",
        "entityType": "azure_sql_table",
        "userDescription": "Core orders data",
        "endorsement": "Certified",
        "domain": "Finance",
        "qualifiedName": "mssql://server/db/orders",
        "contact": [{"id": "u1", "info": "Alice", "contactType": "Owner"}],
        "classification": ["GDPR"],
        "label": ["finance"],
    }
    asset = _parse_search_result(hit)

    assert asset.id == "test-guid"
    assert asset.name == "Orders Table"
    assert asset.endorsement == "Certified"
    assert asset.description == "Core orders data"
    assert len(asset.owners) == 1
    assert asset.owners[0].display_name == "Alice"
    assert asset.owners[0].contact_type == "Owner"
    assert "GDPR" in asset.classification


def test_parse_search_result_handles_missing_fields() -> None:
    hit = {"id": "x", "name": "Empty", "qualifiedName": "q"}
    asset = _parse_search_result(hit)
    assert asset.owners == []
    assert asset.classification == []
    assert asset.endorsement is None


@pytest.mark.asyncio
async def test_search_assets_calls_client(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.search_query.return_value = {
        "value": [{"id": "a1", "name": "Asset1", "qualifiedName": "q1", "entityType": "table"}]
    }
    repo = PurviewCatalogRepository(client=mock_client)
    result = await repo.search_assets("customer", limit=5)

    assert len(result) == 1
    assert result[0].id == "a1"
    mock_client.search_query.assert_called_once_with("customer", 5, None, None)
