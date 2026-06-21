from purview_mcp.application.services.asset_filter import search_assets_filtered
from purview_mcp.domain.entities.asset import Asset
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface
from purview_mcp.shared.observability import Logger


class SearchAssetsUseCase:
    """Search catalog assets, returning only assets that have a description.

    Assets without a description are served by SearchUndocumentedAssetsUseCase.
    """

    def __init__(self, catalog: CatalogRepositoryInterface, log: Logger) -> None:
        self._catalog = catalog
        self._log = log

    async def execute(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
        offset: int = 0,
    ) -> list[Asset]:
        result = await search_assets_filtered(
            self._catalog,
            query,
            limit,
            asset_type,
            classification,
            offset,
            Asset.has_description,
        )
        self._log.info("catalog.search_assets.completed", query=query, count=len(result))
        return result
