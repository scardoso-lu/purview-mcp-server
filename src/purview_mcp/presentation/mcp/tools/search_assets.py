from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.search_assets import SearchAssetsUseCase


def register(mcp: FastMCP, use_case: SearchAssetsUseCase) -> None:
    @mcp.tool()
    async def search_assets(
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
    ) -> dict[str, Any]:
        """Search Microsoft Purview catalog assets by keyword.

        Returns assets with name, type, description, owners, classification tags,
        and endorsement status (Certified / Promoted).

        Args:
            query: Keyword or phrase to search for (e.g. "customer", "sales order").
            limit: Maximum number of results to return (default 10, max 100).
            asset_type: Filter by asset type (e.g. "azure_sql_table", "PowerBIDataset").
            classification: Filter by classification label (e.g. "MICROSOFT.PERSONAL.EMAIL").
        """
        assets = await use_case.execute(query, limit, asset_type, classification)
        return {"assets": [a.model_dump() for a in assets], "count": len(assets)}
