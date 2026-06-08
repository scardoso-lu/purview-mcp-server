from purview_mcp.domain.models.asset import DataQualityMetric
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class GetDataQualityUseCase:
    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(self, guid: str) -> list[DataQualityMetric]:
        asset = await self._catalog.get_asset_by_id(guid)
        return asset.data_quality
