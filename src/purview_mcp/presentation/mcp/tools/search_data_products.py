from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from purview_mcp.application.use_cases.search_data_products import SearchDataProductsUseCase


def register(mcp: FastMCP, use_case: SearchDataProductsUseCase) -> None:
    @mcp.tool()
    async def search_data_products(
        query: str,
        limit: Annotated[int, Field(ge=1, le=100)] = 10,
        domain_id: str | None = None,
        offset: Annotated[int, Field(ge=0, le=10000)] = 0,
    ) -> dict[str, Any]:
        """Search Purview Unified Catalog data products by keyword.

        Data products are curated, governed collections of data assets with owners,
        SLAs, and domain classification.

        Args:
            query: Keyword to search data product names (e.g. "sales", "finance").
            limit: Maximum results to return (default 10, max 100).
            domain_id: Filter by business domain GUID (optional).
            offset: Number of results to skip, for paging (default 0).
        """
        products = await use_case.execute(query, limit, domain_id, offset=offset)
        return {
            "data_products": [p.model_dump() for p in products],
            "count": len(products),
            "offset": offset,
        }
