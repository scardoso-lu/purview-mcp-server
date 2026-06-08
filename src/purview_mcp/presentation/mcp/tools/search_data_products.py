from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.search_data_products import SearchDataProductsUseCase


def register(mcp: FastMCP, use_case: SearchDataProductsUseCase) -> None:
    @mcp.tool()
    async def search_data_products(
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
    ) -> dict[str, Any]:
        """Search Purview Unified Catalog data products by keyword.

        Data products are curated, governed collections of data assets with owners,
        SLAs, and domain classification.

        Args:
            query: Keyword to search data product names (e.g. "sales", "finance").
            limit: Maximum results to return (default 10).
            domain_id: Filter by business domain GUID (optional).
        """
        products = await use_case.execute(query, limit, domain_id)
        return {"data_products": [p.model_dump() for p in products], "count": len(products)}
