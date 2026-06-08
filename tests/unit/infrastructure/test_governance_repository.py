import pytest
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.repositories.purview_governance_repository import (
    PurviewGovernanceRepository,
    _parse_data_product,
    _parse_glossary_term,
)


# --- Glossary term parsing ---

def test_parse_glossary_term_with_attributes_wrapper() -> None:
    raw = {
        "guid": "term-1",
        "attributes": {
            "name": "Customer",
            "qualifiedName": "Glossary.Customer",
            "shortDescription": "An entity that purchases goods.",
            "status": "Approved",
            "synonyms": [{"displayText": "Client"}],
            "stewards": [{"id": "u1"}],
            "experts": [{"id": "u2"}],
        },
    }
    term = _parse_glossary_term(raw)  # type: ignore[arg-type]

    assert term.id == "term-1"
    assert term.name == "Customer"
    assert term.definition == "An entity that purchases goods."
    assert term.status == "Approved"
    assert term.synonyms == ["Client"]
    assert term.stewards == ["u1"]
    assert term.experts == ["u2"]


def test_parse_glossary_term_flat_layout() -> None:
    raw = {
        "termGuid": "term-2",
        "displayText": "Revenue",
        "name": "Revenue",
        "qualifiedName": "Glossary.Revenue",
        "shortDescription": "Total income generated.",
    }
    term = _parse_glossary_term(raw)  # type: ignore[arg-type]

    assert term.id == "term-2"
    assert term.name == "Revenue"
    assert term.definition == "Total income generated."


def test_parse_glossary_term_missing_optional_fields() -> None:
    raw = {"guid": "term-3", "attributes": {"name": "Minimal"}}
    term = _parse_glossary_term(raw)  # type: ignore[arg-type]

    assert term.id == "term-3"
    assert term.name == "Minimal"
    assert term.definition is None
    assert term.synonyms == []
    assert term.stewards == []
    assert term.experts == []


# --- Data product parsing ---

def test_parse_data_product_with_owners() -> None:
    raw = {
        "id": "dp-1",
        "properties": {
            "name": "Sales Product",
            "description": "Sales data.",
            "status": "Active",
            "owners": [{"id": "u1", "displayName": "Alice", "email": "alice@example.com"}],
            "domainId": "domain-1",
            "domainName": "Sales",
            "assetCount": 5,
            "tags": ["core"],
        },
    }
    dp = _parse_data_product(raw)  # type: ignore[arg-type]

    assert dp.id == "dp-1"
    assert dp.name == "Sales Product"
    assert dp.status == "Active"
    assert len(dp.owners) == 1
    assert dp.owners[0].display_name == "Alice"
    assert dp.owners[0].email == "alice@example.com"
    assert dp.asset_count == 5
    assert dp.tags == ["core"]


def test_parse_data_product_empty_owners() -> None:
    raw = {"id": "dp-2", "properties": {"name": "Empty", "owners": None}}
    dp = _parse_data_product(raw)  # type: ignore[arg-type]

    assert dp.id == "dp-2"
    assert dp.owners == []


def test_parse_data_product_null_asset_count_defaults_to_zero() -> None:
    raw = {"id": "dp-3", "properties": {"name": "NullCount", "assetCount": None}}
    dp = _parse_data_product(raw)  # type: ignore[arg-type]

    assert dp.asset_count == 0


# --- Repository integration ---

@pytest.mark.asyncio
async def test_search_glossary_terms_filters_by_query(mocker: MockerFixture) -> None:
    mock_datamap = mocker.AsyncMock()
    mock_datamap.list_glossary_terms.return_value = [
        {"guid": "t1", "attributes": {"name": "Customer", "shortDescription": "buyer"}},
        {"guid": "t2", "attributes": {"name": "Revenue", "shortDescription": "income"}},
        {"guid": "t3", "attributes": {"name": "Customer Segment", "shortDescription": ""}},
    ]
    mock_unified = mocker.AsyncMock()
    repo = PurviewGovernanceRepository(datamap=mock_datamap, unified_catalog=mock_unified)

    results = await repo.search_glossary_terms("customer", limit=10)

    assert len(results) == 2
    assert {r.name for r in results} == {"Customer", "Customer Segment"}


@pytest.mark.asyncio
async def test_search_glossary_terms_fetches_multiplied_limit(mocker: MockerFixture) -> None:
    mock_datamap = mocker.AsyncMock()
    mock_datamap.list_glossary_terms.return_value = []
    mock_unified = mocker.AsyncMock()
    repo = PurviewGovernanceRepository(datamap=mock_datamap, unified_catalog=mock_unified)

    await repo.search_glossary_terms("x", limit=10)

    mock_datamap.list_glossary_terms.assert_called_once_with(limit=20)


@pytest.mark.asyncio
async def test_search_data_products_maps_results(mocker: MockerFixture) -> None:
    mock_datamap = mocker.AsyncMock()
    mock_unified = mocker.AsyncMock()
    mock_unified.query_data_products.return_value = {
        "value": [{"id": "dp-1", "properties": {"name": "Orders Product"}}]
    }
    repo = PurviewGovernanceRepository(datamap=mock_datamap, unified_catalog=mock_unified)

    results = await repo.search_data_products("orders", limit=5)

    assert len(results) == 1
    assert results[0].id == "dp-1"
    mock_unified.query_data_products.assert_called_once_with(
        keyword="orders", limit=5, domain_id=None
    )
