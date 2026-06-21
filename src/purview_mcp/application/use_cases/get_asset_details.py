from purview_mcp.domain.entities.asset import Asset
from purview_mcp.infrastructure.repositories.contract import CatalogRepositoryInterface


class GetAssetDetailsUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> Asset:
        return await self._catalog.get_asset_by_id(guid)
