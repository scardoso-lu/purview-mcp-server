from purview_mcp.domain.models.asset import AssetOwner
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class GetAssetOwnerUseCase:
    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> list[AssetOwner]:
        asset = await self._catalog.get_asset_by_id(guid)
        return asset.owners
