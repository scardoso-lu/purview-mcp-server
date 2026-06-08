from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class SearchAssetsUseCase:
    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
    ) -> list[Asset]:
        return await self._catalog.search_assets(query, limit, asset_type, classification)
