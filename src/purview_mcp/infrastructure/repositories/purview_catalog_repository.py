from typing import cast

from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.infrastructure.api_types import EntityDetailRaw, SearchHitRaw
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient


def _parse_asset(raw: EntityDetailRaw) -> Asset:
    attrs = raw.get("attributes", {})
    contacts = raw.get("contacts", {})
    owners: list[AssetOwner] = []
    for contact_type in ("Expert", "Owner"):
        for contact in contacts.get(contact_type, []):
            owners.append(
                AssetOwner(
                    id=contact.get("id", ""),
                    display_name=contact.get("info", ""),
                    contact_type=contact_type,
                )
            )

    meanings = attrs.get("meanings", [])
    tags = [meaning.get("displayText", "") for meaning in meanings if meaning.get("displayText")]

    dq_raw = attrs.get("dataQualityScore", {})
    dq_metrics: list[DataQualityMetric] = []
    if isinstance(dq_raw, dict):
        for metric_name, metric_val in dq_raw.items():
            dq_metrics.append(DataQualityMetric(name=metric_name, value=metric_val))

    label_raw = raw.get("labels", [])

    return Asset(
        id=raw.get("guid", ""),
        name=attrs.get("name", raw.get("name", "")),
        asset_type=raw.get("typeName", raw.get("entityType", "")),
        description=attrs.get("userDescription") or attrs.get("description"),
        owners=owners,
        classification=[clf.get("typeName", "") for clf in raw.get("classifications", [])],
        endorsement=attrs.get("endorsement"),
        domain=attrs.get("domain"),
        tags=tags + (label_raw if isinstance(label_raw, list) else []),
        qualified_name=attrs.get("qualifiedName", ""),
        collection=raw.get("collectionId"),
        data_quality=dq_metrics,
    )


def _parse_search_result(hit: SearchHitRaw) -> Asset:
    """Parse a search result hit (different shape from entity detail)."""
    owners: list[AssetOwner] = [
        AssetOwner(
            id=contact.get("id", ""),
            display_name=contact.get("info", ""),
            contact_type=contact.get("contactType", "Owner"),
        )
        for contact in hit.get("contact", [])
    ]
    return Asset(
        id=hit.get("id", ""),
        name=hit.get("name", ""),
        asset_type=hit.get("entityType", ""),
        description=hit.get("userDescription") or hit.get("description"),
        owners=owners,
        classification=hit.get("classification", []),
        endorsement=hit.get("endorsement"),
        domain=hit.get("domain"),
        tags=hit.get("label", []),
        qualified_name=hit.get("qualifiedName", ""),
        collection=hit.get("collectionId"),
    )


class PurviewCatalogRepository:
    def __init__(self, client: DataMapClient) -> None:
        self._client = client

    async def search_assets(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
    ) -> list[Asset]:
        result = await self._client.search_query(query, limit, asset_type, classification)
        hits: list[SearchHitRaw] = result.get("value", [])
        return [_parse_search_result(hit) for hit in hits]

    async def get_asset_by_id(self, guid: str) -> Asset:
        result = await self._client.get_entity(guid)
        entity: EntityDetailRaw = cast(EntityDetailRaw, result.get("entity", result))
        return _parse_asset(entity)
