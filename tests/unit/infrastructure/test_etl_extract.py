import httpx
import pytest
import respx

from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient
from purview_mcp.infrastructure.etl.extract import Extractor

_BASE_URL = "https://test.purview.azure.com"
_SEARCH_URL = f"{_BASE_URL}/datamap/api/search/query"


class FakeCredential:
    async def get_token(self) -> str:
        return "test-token"


@pytest.fixture
def extractor() -> Extractor:
    cred = FakeCredential()
    datamap = DataMapClient(_BASE_URL, cred, 30)  # type: ignore[arg-type]
    unified = UnifiedCatalogClient(_BASE_URL, cred, 30)  # type: ignore[arg-type]
    return Extractor(datamap, unified, lineage_depth=2)


@respx.mock
@pytest.mark.asyncio
async def test_enumerate_follows_continuation_token(extractor: Extractor) -> None:
    page1 = httpx.Response(
        200,
        json={
            "@search.count": 3,
            "value": [{"id": "g1", "updateTime": 10}, {"id": "g2", "updateTime": 20}],
            "continuationToken": "tok1",
        },
    )
    page2 = httpx.Response(
        200,
        json={"value": [{"id": "g3", "updateTime": 30}], "continuationToken": None},
    )
    respx.post(_SEARCH_URL).mock(side_effect=[page1, page2])

    result = await extractor.enumerate_assets()

    assert [h.guid for h in result.hits] == ["g1", "g2", "g3"]
    assert result.search_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_enumerate_sends_token_on_second_request(extractor: Extractor) -> None:
    route = respx.post(_SEARCH_URL).mock(
        side_effect=[
            httpx.Response(200, json={"value": [{"id": "g1"}], "continuationToken": "tok1"}),
            httpx.Response(200, json={"value": [], "continuationToken": None}),
        ]
    )
    await extractor.enumerate_assets()

    import json

    first_body = json.loads(route.calls[0].request.content)
    second_body = json.loads(route.calls[1].request.content)
    assert "continuationToken" not in first_body
    assert first_body["offset"] == 0
    assert second_body["continuationToken"] == "tok1"


@respx.mock
@pytest.mark.asyncio
async def test_enumerate_incremental_stops_at_watermark(extractor: Extractor) -> None:
    # Ordered newest-first; paging should stop once updateTime <= watermark (15).
    respx.post(_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": [
                    {"id": "new", "updateTime": 20},
                    {"id": "old", "updateTime": 10},
                ],
                "continuationToken": "more",
            },
        )
    )
    result = await extractor.enumerate_assets(watermark=15)

    assert [h.guid for h in result.hits] == ["new"]


@respx.mock
@pytest.mark.asyncio
async def test_fetch_asset_record_extracts_update_time_and_attrs(extractor: Extractor) -> None:
    respx.get(f"{_BASE_URL}/datamap/api/atlas/v2/entity/guid/g1").mock(
        return_value=httpx.Response(
            200,
            json={
                "entity": {
                    "guid": "g1",
                    "typeName": "azure_sql_table",
                    "updateTime": 12345,
                    "attributes": {"name": "Orders", "qualifiedName": "qn", "userDescription": "d"},
                }
            },
        )
    )
    record = await extractor.fetch_asset_record("g1")

    assert record.asset.id == "g1"
    assert record.asset.name == "Orders"
    assert record.update_time == 12345
    assert record.raw_attributes["qualifiedName"] == "qn"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_lineage_parses_nodes_and_relations(extractor: Extractor) -> None:
    respx.get(f"{_BASE_URL}/datamap/api/atlas/v2/lineage/g1").mock(
        return_value=httpx.Response(
            200,
            json={
                "guidEntityMap": {
                    "up": {"guid": "up", "typeName": "t", "displayText": "Up"},
                    "g1": {"guid": "g1", "typeName": "t", "displayText": "Me"},
                },
                "relations": [{"fromEntityId": "up", "toEntityId": "g1", "relationshipType": "x"}],
            },
        )
    )
    nodes, relations = await extractor.fetch_lineage("g1")

    assert {n.id for n in nodes} == {"up", "g1"}
    assert relations[0].from_id == "up"
    assert relations[0].to_id == "g1"
    assert relations[0].relation_type == "x"


@respx.mock
@pytest.mark.asyncio
async def test_fetch_glossary_terms_pages(extractor: Extractor) -> None:
    # Single short page (< page size) terminates immediately.
    respx.get(f"{_BASE_URL}/datamap/api/atlas/v2/glossary/terms").mock(
        return_value=httpx.Response(200, json=[{"guid": "t1", "attributes": {"name": "Churn"}}])
    )
    terms = await extractor.fetch_glossary_terms()

    assert [t.name for t in terms] == ["Churn"]


@respx.mock
@pytest.mark.asyncio
async def test_fetch_data_products_pages(extractor: Extractor) -> None:
    respx.post(f"{_BASE_URL}/datagovernance/catalog/dataProducts/query").mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "dp1", "properties": {"name": "Sales"}}]}
        )
    )
    products = await extractor.fetch_data_products()

    assert [p.name for p in products] == ["Sales"]
