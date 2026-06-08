from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.get_asset_details import GetAssetDetailsUseCase


def register(mcp: FastMCP, use_case: GetAssetDetailsUseCase) -> None:
    @mcp.tool()
    async def get_asset_details(asset_id: str) -> dict[str, Any]:
        """Retrieve full metadata for a specific Purview asset by its GUID.

        Returns description, owner contacts, domain, classification labels,
        endorsement status, tags, and data quality metrics.

        Args:
            asset_id: The Purview asset GUID (e.g. "3b7b5b3a-1234-...").
        """
        asset = await use_case.execute(asset_id)
        return asset.model_dump()
