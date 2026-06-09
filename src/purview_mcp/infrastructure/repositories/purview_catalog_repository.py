from typing import Any

from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient


def _parse_asset(raw: dict[str, Any]) -> Asset:
    attrs = raw.get("attributes", {})
    contacts = raw.get("contacts", {})
    owners: list[AssetOwner] = []
    for contact_type in ("Expert", "Owner"):
        for contact in contacts.get(contact_type, []):
            owners.append(
                AssetOwner(
                    id=contact.get("id", ""),
                    display_name=contact.get("info", ""),
                    email=contact.get("email") or contact.get("mail") or None,
                    contact_type=contact_type,
                )
            )

    meanings = attrs.get("meanings", [])
    tags = [m.get("displayText", "") for m in meanings if m.get("displayText")]

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
        classification=[c.get("typeName", "") for c in raw.get("classifications", [])],
        endorsement=attrs.get("endorsement"),
        domain=attrs.get("domain"),
        tags=tags + (label_raw if isinstance(label_raw, list) else []),
        qualified_name=attrs.get("qualifiedName", ""),
        collection=raw.get("collectionId"),
        data_quality=dq_metrics,
    )


def _parse_search_result(hit: dict[str, Any]) -> Asset:
    """Parse a search result hit (different shape from entity detail)."""
    contact_list: list[AssetOwner] = []
    for c in hit.get("contact", []):
        contact_list.append(
            AssetOwner(
                id=c.get("id", ""),
                display_name=c.get("info", ""),
                email=c.get("email") or c.get("mail") or None,
                contact_type=c.get("contactType", "Owner"),
            )
        )
    return Asset(
        id=hit.get("id", ""),
        name=hit.get("name", ""),
        asset_type=hit.get("entityType", ""),
        description=hit.get("userDescription") or hit.get("description"),
        owners=contact_list,
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
        offset: int = 0,
    ) -> list[Asset]:
        result: Any = await self._client.search_query(
            query, limit, asset_type, classification, offset=offset
        )
        hits: list[dict[str, Any]] = result.get("value", [])
        return [_parse_search_result(h) for h in hits]

    async def get_asset_by_id(self, guid: str) -> Asset:
        result: Any = await self._client.get_entity(guid)
        entity: dict[str, Any] = result.get("entity", result)
        return _parse_asset(entity)
