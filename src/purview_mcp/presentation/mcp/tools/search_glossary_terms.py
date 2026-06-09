from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from purview_mcp.application.use_cases.search_glossary_terms import SearchGlossaryTermsUseCase


def register(mcp: FastMCP, use_case: SearchGlossaryTermsUseCase) -> None:
    @mcp.tool()
    async def search_glossary_terms(
        query: str,
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
        offset: Annotated[int, Field(ge=0, le=10000)] = 0,
    ) -> dict[str, Any]:
        """Search the Purview business glossary for terms matching a keyword.

        Returns term definitions, status (Approved/Draft), synonyms, and stewards.
        Useful for understanding the canonical business meaning of data concepts.

        Args:
            query: Business term to look up (e.g. "customer", "revenue", "churn").
            limit: Maximum number of terms to return (default 25, max 100).
            offset: Number of matching terms to skip, for paging (default 0).
        """
        terms = await use_case.execute(query, limit, offset=offset)
        return {"terms": [t.model_dump() for t in terms], "count": len(terms), "offset": offset}
