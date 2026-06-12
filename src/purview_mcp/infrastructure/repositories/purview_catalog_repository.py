from typing import Any

from purview_mcp.domain.models.asset import Asset
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient

# Re-exported for backward compatibility (tests and the ETL import these).
from purview_mcp.infrastructure.repositories._parsers import (  # noqa: F401
    _parse_asset,
    _parse_search_result,
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
