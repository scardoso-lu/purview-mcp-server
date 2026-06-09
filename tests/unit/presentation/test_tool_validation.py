import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pytest_mock import MockerFixture

from purview_mcp.presentation.mcp.tools import (
    get_asset_lineage,
    search_assets,
    search_glossary_terms,
)


@pytest.fixture
def mcp() -> FastMCP:
    return FastMCP("test")


@pytest.mark.asyncio
async def test_lineage_depth_above_max_rejected(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    get_asset_lineage.register(mcp, use_case)

    with pytest.raises(ToolError):
        await mcp.call_tool("get_asset_lineage", {"asset_id": "g1", "depth": 7})
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_lineage_invalid_direction_rejected(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    get_asset_lineage.register(mcp, use_case)

    with pytest.raises(ToolError):
        await mcp.call_tool("get_asset_lineage", {"asset_id": "g1", "direction": "SIDEWAYS"})
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_lineage_depth_at_max_accepted(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    use_case.execute.return_value = mocker.MagicMock(model_dump=lambda: {"nodes": []})
    get_asset_lineage.register(mcp, use_case)

    await mcp.call_tool("get_asset_lineage", {"asset_id": "g1", "depth": 6})
    use_case.execute.assert_awaited_once_with("g1", "BOTH", 6)


@pytest.mark.asyncio
async def test_search_assets_limit_above_max_rejected(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    search_assets.register(mcp, use_case)

    with pytest.raises(ToolError):
        await mcp.call_tool("search_assets", {"query": "x", "limit": 101})
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_assets_limit_zero_rejected(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    search_assets.register(mcp, use_case)

    with pytest.raises(ToolError):
        await mcp.call_tool("search_assets", {"query": "x", "limit": 0})
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_assets_negative_offset_rejected(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    search_assets.register(mcp, use_case)

    with pytest.raises(ToolError):
        await mcp.call_tool("search_assets", {"query": "x", "offset": -1})
    use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_assets_valid_bounds_accepted(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    use_case.execute.return_value = []
    search_assets.register(mcp, use_case)

    await mcp.call_tool("search_assets", {"query": "x", "limit": 100, "offset": 50})
    use_case.execute.assert_awaited_once_with("x", 100, None, None, offset=50)


@pytest.mark.asyncio
async def test_search_glossary_terms_passes_offset(mcp: FastMCP, mocker: MockerFixture) -> None:
    use_case = mocker.AsyncMock()
    use_case.execute.return_value = []
    search_glossary_terms.register(mcp, use_case)

    await mcp.call_tool("search_glossary_terms", {"query": "churn", "offset": 5})
    use_case.execute.assert_awaited_once_with("churn", 25, offset=5)
