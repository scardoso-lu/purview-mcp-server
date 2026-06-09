import pytest
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.repositories.purview_governance_repository import (
    PurviewGovernanceRepository,
    _parse_data_product,
    _parse_glossary_term,
)


def _term(name: str, description: str = "") -> dict[str, object]:
    return {
        "guid": f"guid-{name}",
        "attributes": {
            "name": name,
            "qualifiedName": f"{name}@glossary",
            "shortDescription": description,
        },
    }


def test_parse_glossary_term_nested_attributes() -> None:
    term = _parse_glossary_term(
        {
            "guid": "g1",
            "attributes": {
                "name": "Customer",
                "qualifiedName": "Customer@glossary",
                "shortDescription": "A buyer",
                "status": "Approved",
                "synonyms": [{"displayText": "Client"}],
                "stewards": [{"id": "u1"}],
            },
        }
    )
    assert term.id == "g1"
    assert term.name == "Customer"
    assert term.definition == "A buyer"
    assert term.synonyms == ["Client"]
    assert term.stewards == ["u1"]


def test_parse_glossary_term_flat_shape() -> None:
    term = _parse_glossary_term({"termGuid": "t1", "displayText": "Churn"})
    assert term.id == "t1"
    assert term.name == "Churn"
    assert term.synonyms == []
    assert term.stewards == []


def test_parse_data_product_missing_properties() -> None:
    product = _parse_data_product({"id": "dp1", "name": "Sales"})
    assert product.id == "dp1"
    assert product.name == "Sales"
    assert product.owners == []
    assert product.asset_count == 0
    assert product.tags == []


def test_parse_data_product_null_fields() -> None:
    product = _parse_data_product(
        {
            "id": "dp1",
            "properties": {"name": "Sales", "owners": None, "assetCount": None, "tags": None},
        }
    )
    assert product.owners == []
    assert product.asset_count == 0
    assert product.tags == []


@pytest.mark.asyncio
async def test_search_glossary_terms_filters_by_keyword(mocker: MockerFixture) -> None:
    datamap = mocker.AsyncMock()
    datamap.list_glossary_terms.return_value = [
        _term("Customer"),
        _term("Revenue", description="customer spend"),
        _term("Inventory"),
    ]
    repo = PurviewGovernanceRepository(datamap, mocker.AsyncMock())
    terms = await repo.search_glossary_terms("customer", limit=10)

    assert [t.name for t in terms] == ["Customer", "Revenue"]
    datamap.list_glossary_terms.assert_called_once_with(limit=20)


@pytest.mark.asyncio
async def test_search_glossary_terms_applies_offset(mocker: MockerFixture) -> None:
    datamap = mocker.AsyncMock()
    datamap.list_glossary_terms.return_value = [
        _term("Customer A"),
        _term("Customer B"),
        _term("Customer C"),
    ]
    repo = PurviewGovernanceRepository(datamap, mocker.AsyncMock())
    terms = await repo.search_glossary_terms("customer", limit=1, offset=1)

    assert [t.name for t in terms] == ["Customer B"]
    datamap.list_glossary_terms.assert_called_once_with(limit=4)


@pytest.mark.asyncio
async def test_search_data_products_passes_skip(mocker: MockerFixture) -> None:
    unified = mocker.AsyncMock()
    unified.query_data_products.return_value = {"value": []}
    repo = PurviewGovernanceRepository(mocker.AsyncMock(), unified)
    result = await repo.search_data_products("sales", limit=5, offset=10)

    assert result == []
    unified.query_data_products.assert_called_once_with(
        keyword="sales", limit=5, domain_id=None, skip=10
    )
