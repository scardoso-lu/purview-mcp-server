from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.get_asset_owner import GetAssetOwnerUseCase


def register(mcp: FastMCP, use_case: GetAssetOwnerUseCase) -> None:
    @mcp.tool()
    async def get_asset_owner(asset_id: str) -> dict[str, Any]:
        """Return business and technical owners for a Purview asset.

        Returns contacts with their type (Owner or Expert), display name, and email.

        Args:
            asset_id: The Purview asset GUID.
        """
        owners = await use_case.execute(asset_id)
        return {"owners": [o.model_dump() for o in owners], "count": len(owners)}
