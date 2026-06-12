from typing import Any

from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient

# Re-exported for backward compatibility (tests and the ETL import these).
from purview_mcp.infrastructure.repositories._parsers import (  # noqa: F401
    _parse_data_product,
    _parse_glossary_term,
)


class PurviewGovernanceRepository:
    def __init__(
        self,
        datamap: DataMapClient,
        unified_catalog: UnifiedCatalogClient,
    ) -> None:
        self._datamap = datamap
        self._unified = unified_catalog

    async def search_glossary_terms(
        self, query: str, limit: int = 25, offset: int = 0
    ) -> list[GlossaryTerm]:
        # Keyword filtering happens client-side, so the API-level offset cannot be
        # used directly. Over-fetch proportionally to (offset + limit) and slice the
        # filtered matches — a best-effort approximation for small glossaries.
        raw_terms: list[Any] = await self._datamap.list_glossary_terms(limit=(offset + limit) * 2)
        query_lower = query.lower()
        matched: list[dict[str, Any]] = [
            t
            for t in raw_terms
            if query_lower in (t.get("attributes", t).get("name", "")).lower()
            or query_lower in (t.get("attributes", t).get("shortDescription", "") or "").lower()
        ]
        return [_parse_glossary_term(t) for t in matched[offset : offset + limit]]

    async def search_data_products(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
        offset: int = 0,
    ) -> list[DataProduct]:
        result: Any = await self._unified.query_data_products(
            keyword=query, limit=limit, domain_id=domain_id, skip=offset
        )
        items: list[dict[str, Any]] = result.get("value", [])
        return [_parse_data_product(item) for item in items]
