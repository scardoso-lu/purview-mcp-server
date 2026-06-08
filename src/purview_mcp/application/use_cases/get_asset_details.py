from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class GetAssetDetailsUseCase:
    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> Asset:
        return await self._catalog.get_asset_by_id(guid)
