from purview_mcp.domain.entities.asset import AssetOwner
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface
from purview_mcp.shared.observability import Logger


class GetAssetOwnerUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface, log: Logger) -> None:
        self._catalog = catalog
        self._log = log

    async def execute(self, guid: str) -> list[AssetOwner]:
        asset = await self._catalog.get_asset_by_id(guid)
        self._log.info("catalog.get_asset_owner.completed", guid=guid, count=len(asset.owners))
        return asset.owners
