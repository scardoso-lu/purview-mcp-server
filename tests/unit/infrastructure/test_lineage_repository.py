import pytest
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.repositories.purview_lineage_repository import (
    PurviewLineageRepository,
    _parse_node,
)


def test_parse_node_prefers_display_text_over_attributes_name() -> None:
    node = {
        "guid": "n1",
        "displayText": "Orders Table",
        "typeName": "azure_sql_table",
        "attributes": {"name": "orders", "qualifiedName": "mssql://server/db/orders"},
    }
    result = _parse_node(node)  # type: ignore[arg-type]

    assert result.id == "n1"
    assert result.name == "Orders Table"
    assert result.asset_type == "azure_sql_table"
    assert result.qualified_name == "mssql://server/db/orders"


def test_parse_node_falls_back_to_attributes_name_when_no_display_text() -> None:
    node = {
        "guid": "n2",
        "typeName": "PowerBIDataset",
        "attributes": {"name": "Sales Dashboard", "qualifiedName": "pbi://sales"},
    }
    result = _parse_node(node)  # type: ignore[arg-type]

    assert result.name == "Sales Dashboard"


def test_parse_node_missing_fields_use_empty_strings() -> None:
    node: dict[str, str] = {}
    result = _parse_node(node)  # type: ignore[arg-type]

    assert result.id == ""
    assert result.name == ""
    assert result.asset_type == ""
    assert result.qualified_name == ""


@pytest.mark.asyncio
async def test_get_lineage_classifies_upstream_and_downstream(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.get_lineage.return_value = {
        "guidEntityMap": {
            "src-1": {"guid": "src-1", "displayText": "Source", "typeName": "table", "attributes": {"qualifiedName": "q/src"}},
            "dst-1": {"guid": "dst-1", "displayText": "Dest", "typeName": "view", "attributes": {"qualifiedName": "q/dst"}},
        },
        "relations": [
            {"fromEntityId": "src-1", "toEntityId": "focus-guid", "relationshipType": "DataFlow"},
            {"fromEntityId": "focus-guid", "toEntityId": "dst-1", "relationshipType": "DataFlow"},
        ],
    }
    repo = PurviewLineageRepository(client=mock_client)

    graph = await repo.get_lineage("focus-guid", direction="BOTH", depth=3)

    assert graph.asset_id == "focus-guid"
    assert len(graph.upstream) == 1
    assert graph.upstream[0].id == "src-1"
    assert len(graph.downstream) == 1
    assert graph.downstream[0].id == "dst-1"
    assert len(graph.relations) == 2


@pytest.mark.asyncio
async def test_get_lineage_ignores_unknown_guids(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.get_lineage.return_value = {
        "guidEntityMap": {},
        "relations": [
            {"fromEntityId": "ghost-1", "toEntityId": "focus-guid"},
        ],
    }
    repo = PurviewLineageRepository(client=mock_client)

    graph = await repo.get_lineage("focus-guid")

    assert graph.upstream == []
    assert graph.downstream == []
    assert len(graph.relations) == 1


@pytest.mark.asyncio
async def test_get_lineage_empty_response(mocker: MockerFixture) -> None:
    mock_client = mocker.AsyncMock()
    mock_client.get_lineage.return_value = {}
    repo = PurviewLineageRepository(client=mock_client)

    graph = await repo.get_lineage("empty-guid")

    assert graph.upstream == []
    assert graph.downstream == []
    assert graph.relations == []
