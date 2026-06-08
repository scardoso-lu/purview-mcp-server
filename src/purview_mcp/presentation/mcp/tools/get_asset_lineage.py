from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.get_asset_lineage import GetAssetLineageUseCase


def register(mcp: FastMCP, use_case: GetAssetLineageUseCase) -> None:
    @mcp.tool()
    async def get_asset_lineage(
        asset_id: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Return upstream and downstream data lineage for an asset.

        Traces data flow from source systems to consuming reports and dashboards.

        Args:
            asset_id: The Purview asset GUID.
            direction: "BOTH" (default), "INPUT" (upstream only), or "OUTPUT" (downstream only).
            depth: Number of lineage hops to traverse (default 3, max 6).
        """
        graph = await use_case.execute(asset_id, direction, depth)
        return graph.model_dump()
