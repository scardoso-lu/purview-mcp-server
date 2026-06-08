from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.get_data_quality import GetDataQualityUseCase


def register(mcp: FastMCP, use_case: GetDataQualityUseCase) -> None:
    @mcp.tool()
    async def get_data_quality(asset_id: str) -> dict[str, Any]:
        """Return data quality metrics and scores for a Purview asset.

        Retrieves quality rules, scores, and rule statuses attached to the asset
        in the Purview data quality framework.

        Args:
            asset_id: The Purview asset GUID.
        """
        metrics = await use_case.execute(asset_id)
        return {
            "asset_id": asset_id,
            "metrics": [m.model_dump() for m in metrics],
            "count": len(metrics),
        }
