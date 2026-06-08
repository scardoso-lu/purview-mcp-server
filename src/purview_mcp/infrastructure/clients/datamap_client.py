from typing import Any

from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider
from purview_mcp.infrastructure.clients.base_client import BaseClient

_SEARCH_API_VERSION = "2023-09-01"
_ATLAS_BASE = "/datamap/api/atlas/v2"
_SEARCH_BASE = "/datamap/api"


class DataMapClient(BaseClient):
    """Client for the Purview DataMap / Atlas v2 API."""

    def __init__(
        self, endpoint: str, credential: PurviewCredentialProvider, timeout: int = 30
    ) -> None:
        super().__init__(endpoint, credential, timeout)

    async def search_query(
        self,
        keyword: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "keywords": keyword,
            "limit": limit,
            "offset": 0,
        }
        filters: list[dict[str, Any]] = []
        if asset_type:
            filters.append({"entityType": asset_type, "includeSubTypes": True})
        if classification:
            filters.append({"classification": classification})
        if filters:
            body["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

        return await self.post(
            f"{_SEARCH_BASE}/search/query?api-version={_SEARCH_API_VERSION}", body
        )

    async def get_entity(self, guid: str) -> Any:
        return await self.get(f"{_ATLAS_BASE}/entity/guid/{guid}")

    async def get_lineage(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> Any:
        return await self.get(
            f"{_ATLAS_BASE}/lineage/{guid}",
            params={"direction": direction, "depth": depth},
        )

    async def list_glossary_terms(self, limit: int = 25, offset: int = 0) -> list[Any]:
        result: Any = await self.get(
            f"{_ATLAS_BASE}/glossary/terms",
            params={"limit": limit, "offset": offset},
        )
        return result if isinstance(result, list) else result.get("value", [])
