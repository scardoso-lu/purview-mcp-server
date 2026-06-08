from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.search_glossary_terms import SearchGlossaryTermsUseCase


def register(mcp: FastMCP, use_case: SearchGlossaryTermsUseCase) -> None:
    @mcp.tool()
    async def search_glossary_terms(query: str, limit: int = 25) -> dict[str, Any]:
        """Search the Purview business glossary for terms matching a keyword.

        Returns term definitions, status (Approved/Draft), synonyms, and stewards.
        Useful for understanding the canonical business meaning of data concepts.

        Args:
            query: Business term to look up (e.g. "customer", "revenue", "churn").
            limit: Maximum number of terms to return (default 25).
        """
        terms = await use_case.execute(query, limit)
        return {"terms": [t.model_dump() for t in terms], "count": len(terms)}
