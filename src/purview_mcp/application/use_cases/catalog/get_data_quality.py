from purview_mcp.domain.entities.asset import DataQualityMetric
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface
from purview_mcp.shared.observability import Logger


class GetDataQualityUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface, log: Logger) -> None:
        self._catalog = catalog
        self._log = log

    async def execute(self, guid: str) -> list[DataQualityMetric]:
        asset = await self._catalog.get_asset_by_id(guid)
        self._log.info(
            "catalog.get_data_quality.completed", guid=guid, count=len(asset.data_quality)
        )
        return asset.data_quality
