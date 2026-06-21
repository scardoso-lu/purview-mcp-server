from purview_mcp.domain.entities.asset import Asset
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface
from purview_mcp.shared.observability import Logger


class GetAssetDetailsUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface, log: Logger) -> None:
        self._catalog = catalog
        self._log = log

    async def execute(self, guid: str) -> Asset:
        result = await self._catalog.get_asset_by_id(guid)
        self._log.info("catalog.get_asset_details.completed", guid=guid)
        return result
