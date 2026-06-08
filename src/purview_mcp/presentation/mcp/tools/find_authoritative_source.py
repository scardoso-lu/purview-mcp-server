from typing import Any

from mcp.server.fastmcp import FastMCP

from purview_mcp.application.use_cases.find_authoritative_source import (
    FindAuthoritativeSourceUseCase,
)


def register(mcp: FastMCP, use_case: FindAuthoritativeSourceUseCase) -> None:
    @mcp.tool()
    async def find_authoritative_source(concept: str, limit: int = 10) -> dict[str, Any]:
        """Identify the most trusted and authoritative dataset for a business concept.

        Scores candidate assets using governance signals: Certified endorsement,
        assigned owners, description completeness, and domain classification.
        Returns the top-ranked asset with a plain-language explanation.

        Args:
            concept: Business concept to find the authoritative source for
                     (e.g. "customer", "product hierarchy", "financial transactions").
            limit: Number of candidate assets to evaluate (default 10).
        """
        result = await use_case.execute(concept, limit)
        if result is None:
            return {"found": False, "message": f"No assets found for concept: '{concept}'"}
        return {
            "found": True,
            "authoritative_asset": result.asset.model_dump(),
            "score": result.score,
            "explanation": result.explanation,
            "alternatives": [a.model_dump() for a in result.alternatives],
        }
