from purview_mcp.domain.entities.asset import DataQualityMetric
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface


class GetDataQualityUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> list[DataQualityMetric]:
        asset = await self._catalog.get_asset_by_id(guid)
        return asset.data_quality
