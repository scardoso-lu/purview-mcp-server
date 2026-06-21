from purview_mcp.domain.entities.asset import AssetOwner
from purview_mcp.infrastructure.repositories.contract import CatalogRepositoryInterface


class GetAssetOwnerUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> list[AssetOwner]:
        asset = await self._catalog.get_asset_by_id(guid)
        return asset.owners
