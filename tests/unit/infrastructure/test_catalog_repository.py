import pytest
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.repositories.purview_catalog_repository import (
    PurviewCatalogRepository,
    _parse_asset,
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
    mock_client.search_query.assert_called_once_with("customer", 5, None, None, offset=0)


@pytest.mark.asyncio
async def test_search_assets_passes_offset(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.search_query.return_value = {"value": []}
    repo = PurviewCatalogRepository(client=mock_client)
    result = await repo.search_assets("customer", limit=5, offset=20)

    assert result == []
    mock_client.search_query.assert_called_once_with("customer", 5, None, None, offset=20)


def test_parse_search_result_extracts_email() -> None:
    hit = {
        "id": "x",
        "name": "Asset",
        "qualifiedName": "q",
        "contact": [
            {"id": "u1", "info": "Alice", "contactType": "Owner", "email": "alice@contoso.com"},
            {"id": "u2", "info": "Bob", "contactType": "Expert", "mail": "bob@contoso.com"},
            {"id": "u3", "info": "Carol", "contactType": "Owner"},
        ],
    }
    asset = _parse_search_result(hit)
    assert asset.owners[0].email == "alice@contoso.com"
    assert asset.owners[1].email == "bob@contoso.com"
    assert asset.owners[2].email is None


def test_parse_search_result_handles_malformed_contacts() -> None:
    hit = {"id": "x", "name": "Asset", "qualifiedName": "q", "contact": [{}]}
    asset = _parse_search_result(hit)
    assert asset.owners[0].id == ""
    assert asset.owners[0].email is None


def test_parse_asset_extracts_owner_email() -> None:
    raw = {
        "guid": "g1",
        "typeName": "azure_sql_table",
        "attributes": {"name": "Orders", "qualifiedName": "q"},
        "contacts": {
            "Owner": [{"id": "u1", "info": "Alice", "email": "alice@contoso.com"}],
            "Expert": [{"id": "u2", "info": "Bob"}],
        },
    }
    asset = _parse_asset(raw)
    emails = {o.id: o.email for o in asset.owners}
    assert emails == {"u1": "alice@contoso.com", "u2": None}


def test_parse_asset_handles_non_dict_data_quality() -> None:
    raw = {
        "guid": "g1",
        "typeName": "table",
        "attributes": {"name": "Orders", "qualifiedName": "q", "dataQualityScore": 0.9},
    }
    asset = _parse_asset(raw)
    assert asset.data_quality == []


@pytest.mark.asyncio
async def test_search_assets_handles_empty_response(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.search_query.return_value = {}
    repo = PurviewCatalogRepository(client=mock_client)
    assert await repo.search_assets("nothing") == []
