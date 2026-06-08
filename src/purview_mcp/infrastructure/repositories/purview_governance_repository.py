from typing import cast

from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.infrastructure.api_types import DataProductRaw, GlossaryTermRaw
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient

# Fetch a multiple of the requested limit to compensate for in-memory filtering losses.
_GLOSSARY_FETCH_MULTIPLIER = 2


def _term_attrs(raw: GlossaryTermRaw) -> GlossaryTermRaw:
    # The DataMap list endpoint nests term fields under "attributes";
    # direct-lookup endpoints return them at the root level.
    return cast(GlossaryTermRaw, raw.get("attributes", raw))


def _parse_glossary_term(raw: GlossaryTermRaw) -> GlossaryTerm:
    attrs = _term_attrs(raw)
    return GlossaryTerm(
        id=raw.get("guid", raw.get("termGuid", "")),
        name=attrs.get("name", raw.get("displayText", "")),
        qualified_name=attrs.get("qualifiedName", ""),
        definition=attrs.get("shortDescription") or attrs.get("definition"),
        status=attrs.get("status"),
        long_description=attrs.get("longDescription"),
        examples=attrs.get("examples", []) or [],
        synonyms=[synonym.get("displayText", "") for synonym in (attrs.get("synonyms") or [])],
        stewards=[steward.get("id", "") for steward in (attrs.get("stewards") or [])],
        experts=[expert.get("id", "") for expert in (attrs.get("experts") or [])],
    )


def _parse_data_product(raw: DataProductRaw) -> DataProduct:
    props = raw.get("properties", {})
    owners: list[DataProductOwner] = [
        DataProductOwner(
            id=owner_data.get("id", ""),
            display_name=owner_data.get("displayName"),
            email=owner_data.get("email"),
        )
        for owner_data in (props.get("owners", []) or [])
    ]
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

    async def search_glossary_terms(self, query: str, limit: int = 25) -> list[GlossaryTerm]:
        raw_terms: list[GlossaryTermRaw] = await self._datamap.list_glossary_terms(
            limit=limit * _GLOSSARY_FETCH_MULTIPLIER
        )
        query_lower = query.lower()
        matched = [
            term
            for term in raw_terms
            if _matches_glossary_query(term, query_lower)
        ]
        return [_parse_glossary_term(term) for term in matched[:limit]]

    async def search_data_products(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
    ) -> list[DataProduct]:
        result = await self._unified.query_data_products(
            keyword=query, limit=limit, domain_id=domain_id
        )
        items: list[DataProductRaw] = result.get("value", [])
        return [_parse_data_product(item) for item in items]


def _matches_glossary_query(term: GlossaryTermRaw, query_lower: str) -> bool:
    attrs = _term_attrs(term)
    name = attrs.get("name", "").lower()
    description = (attrs.get("shortDescription", "") or "").lower()
    return query_lower in name or query_lower in description
