"""Extract layer: pull all Purview catalog data via the existing API clients.

Full enumeration uses the Discovery/Query API's ``continuationToken`` cursor,
which streams the entire result set with no offset-window ceiling (offset paging
caps around ~210k results). Per-asset detail and lineage reuse the existing
clients and the shared ``_parsers`` so the database holds exactly the domain
models the live path produces.
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageNode, LineageRelation
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient
from purview_mcp.infrastructure.etl.load import AssetRecord
from purview_mcp.infrastructure.repositories._parsers import (
    _parse_asset,
    _parse_data_product,
    _parse_glossary_term,
    _parse_node,
)

logger = structlog.get_logger(__name__)

_PAGE_SIZE = 1000


@dataclass
class AssetHit:
    guid: str
    update_time: int | None


@dataclass
class Enumeration:
    hits: list[AssetHit] = field(default_factory=list)
    search_count: int | None = None  # @search.count, for the completeness check


def _hit_guid(hit: dict[str, Any]) -> str:
    return hit.get("id") or hit.get("guid") or ""


def _hit_update_time(hit: dict[str, Any]) -> int | None:
    val = hit.get("updateTime")
    return int(val) if isinstance(val, (int, float)) else None


def _entity_update_time(entity: dict[str, Any]) -> int | None:
    val = entity.get("updateTime")
    if isinstance(val, (int, float)):
        return int(val)
    attrs = entity.get("attributes", {})
    ts = attrs.get("lastModifiedTS")
    try:
        return int(ts) if ts is not None else None
    except (TypeError, ValueError):
        return None


class Extractor:
    def __init__(
        self,
        datamap: DataMapClient,
        unified: UnifiedCatalogClient,
        lineage_depth: int = 3,
    ) -> None:
        self._datamap = datamap
        self._unified = unified
        self._lineage_depth = lineage_depth

    async def enumerate_assets(self, watermark: int | None = None) -> Enumeration:
        """Enumerate asset GUIDs via continuationToken paging.

        When ``watermark`` is given (incremental), results are ordered by
        ``updateTime`` descending and paging stops once a hit is at or below the
        watermark.
        """
        orderby = [{"updateTime": "DESC"}] if watermark is not None else None
        token: str | None = None
        first = True
        out = Enumeration()
        while True:
            result: Any = await self._datamap.search_query(
                keyword="",
                limit=_PAGE_SIZE,
                continuation_token=token,
                orderby=orderby,
            )
            if first:
                out.search_count = result.get("@search.count")
                first = False
            hits: list[dict[str, Any]] = result.get("value", []) or []
            stop = False
            for hit in hits:
                ut = _hit_update_time(hit)
                if watermark is not None and ut is not None and ut <= watermark:
                    stop = True
                    break
                guid = _hit_guid(hit)
                if guid:
                    out.hits.append(AssetHit(guid=guid, update_time=ut))
            token = result.get("continuationToken")
            if stop or not hits or not token:
                break
        logger.info(
            "etl.enumerate.complete",
            enumerated=len(out.hits),
            search_count=out.search_count,
            incremental=watermark is not None,
        )
        return out

    async def fetch_asset_record(self, guid: str) -> AssetRecord:
        result: Any = await self._datamap.get_entity(guid)
        entity: dict[str, Any] = result.get("entity", result)
        asset = _parse_asset(entity)
        return AssetRecord(
            asset=asset,
            update_time=_entity_update_time(entity),
            raw_attributes=entity.get("attributes") or None,
        )

    async def fetch_lineage(self, guid: str) -> tuple[list[LineageNode], list[LineageRelation]]:
        raw: Any = await self._datamap.get_lineage(guid, "BOTH", self._lineage_depth)
        guid_entity_map: dict[str, dict[str, Any]] = raw.get("guidEntityMap", {}) or {}
        relations_raw: list[dict[str, Any]] = raw.get("relations", []) or []
        nodes = [_parse_node(node) for node in guid_entity_map.values()]
        relations = [
            LineageRelation(
                from_id=r.get("fromEntityId", ""),
                to_id=r.get("toEntityId", ""),
                relation_type=r.get("relationshipType"),
            )
            for r in relations_raw
        ]
        return nodes, relations

    async def fetch_glossary_terms(self) -> list[GlossaryTerm]:
        terms: list[GlossaryTerm] = []
        offset = 0
        while True:
            raw = await self._datamap.list_glossary_terms(limit=_PAGE_SIZE, offset=offset)
            if not raw:
                break
            terms.extend(_parse_glossary_term(t) for t in raw)
            if len(raw) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE
        logger.info("etl.glossary.complete", count=len(terms))
        return terms

    async def fetch_data_products(self) -> list[DataProduct]:
        products: list[DataProduct] = []
        skip = 0
        while True:
            result: Any = await self._unified.query_data_products(limit=_PAGE_SIZE, skip=skip)
            items: list[dict[str, Any]] = result.get("value", []) or []
            if not items:
                break
            products.extend(_parse_data_product(i) for i in items)
            if len(items) < _PAGE_SIZE:
                break
            skip += _PAGE_SIZE
        logger.info("etl.data_products.complete", count=len(products))
        return products
