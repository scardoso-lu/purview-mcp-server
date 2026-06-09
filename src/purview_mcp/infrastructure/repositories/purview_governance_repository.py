from typing import Any

from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient


def _parse_glossary_term(raw: dict[str, Any]) -> GlossaryTerm:
    attrs: dict[str, Any] = raw.get("attributes", raw)
    return GlossaryTerm(
        id=raw.get("guid", raw.get("termGuid", "")),
        name=attrs.get("name", raw.get("displayText", "")),
        qualified_name=attrs.get("qualifiedName", ""),
        definition=attrs.get("shortDescription") or attrs.get("definition"),
        status=attrs.get("status"),
        long_description=attrs.get("longDescription"),
        examples=attrs.get("examples", []) or [],
        synonyms=[s.get("displayText", "") for s in (attrs.get("synonyms") or [])],
        stewards=[s.get("id", "") for s in (attrs.get("stewards") or [])],
        experts=[e.get("id", "") for e in (attrs.get("experts") or [])],
    )


def _parse_data_product(raw: dict[str, Any]) -> DataProduct:
    props: dict[str, Any] = raw.get("properties", raw)
    owners: list[DataProductOwner] = []
    for o in props.get("owners", []) or []:
        owners.append(
            DataProductOwner(
                id=o.get("id", ""),
                display_name=o.get("displayName"),
                email=o.get("email"),
            )
        )
    return DataProduct(
        id=raw.get("id", ""),
        name=props.get("name", raw.get("name", "")),
        description=props.get("description"),
        status=props.get("status"),
        owners=owners,
        domain_id=props.get("domainId"),
        domain_name=props.get("domainName"),
        asset_count=props.get("assetCount", 0) or 0,
        tags=props.get("tags", []) or [],
        data_product_type=props.get("dataProductType"),
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
