from purview_mcp.application.use_cases.search_assets import FETCH_CAP
from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class SearchUndocumentedAssetsUseCase:
    """Search catalog assets that are missing a description.

    Complements SearchAssetsUseCase, which returns only documented assets.
    """

    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
        offset: int = 0,
    ) -> list[Asset]:
        fetch_size = min((offset + limit) * 2, FETCH_CAP)
        assets = await self._catalog.search_assets(
            query, fetch_size, asset_type, classification, offset=0
        )
        undocumented = [a for a in assets if not a.has_description()]
        return undocumented[offset : offset + limit]
