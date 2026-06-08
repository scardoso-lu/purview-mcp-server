from typing import Protocol

from purview_mcp.domain.models.asset import Asset


class ICatalogRepository(Protocol):
    async def search_assets(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
    ) -> list[Asset]: ...

    async def get_asset_by_id(self, guid: str) -> Asset: ...
