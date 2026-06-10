from purview_mcp.application.use_cases.asset_search import search_assets_filtered
from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository


class SearchAssetsUseCase:
    """Search catalog assets, returning only assets that have a description.

    Assets without a description are served by SearchUndocumentedAssetsUseCase.
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
        return await search_assets_filtered(
            self._catalog,
            query,
            limit,
            asset_type,
            classification,
            offset,
            Asset.has_description,
        )
