from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from purview_mcp.application.use_cases.search_undocumented_assets import (
    SearchUndocumentedAssetsUseCase,
)


def register(mcp: FastMCP, use_case: SearchUndocumentedAssetsUseCase) -> None:
    @mcp.tool()
    async def search_undocumented_assets(
        query: str,
        limit: Annotated[int, Field(ge=1, le=100)] = 10,
        asset_type: str | None = None,
        classification: str | None = None,
        offset: Annotated[int, Field(ge=0, le=10000)] = 0,
    ) -> dict[str, Any]:
        """Search Microsoft Purview catalog assets that are MISSING a description.

        Complements search_assets, which returns only documented assets. Use this
        to surface assets that need documentation, or to include undocumented
        assets in discovery.

        Args:
            query: Keyword or phrase to search for (e.g. "customer", "sales order").
            limit: Maximum number of results to return (default 10, max 100).
            asset_type: Filter by asset type (e.g. "azure_sql_table", "PowerBIDataset").
            classification: Filter by classification label (e.g. "MICROSOFT.PERSONAL.EMAIL").
            offset: Number of results to skip, for paging (default 0).
        """
        assets = await use_case.execute(query, limit, asset_type, classification, offset=offset)
        return {"assets": [a.model_dump() for a in assets], "count": len(assets), "offset": offset}
