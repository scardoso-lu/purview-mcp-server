from purview_mcp.application.services.asset_filter import search_assets_filtered
from purview_mcp.domain.entities.asset import Asset
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface


class SearchUndocumentedAssetsUseCase:
    """Search catalog assets that are missing a description.

    Complements SearchAssetsUseCase, which returns only documented assets.
    """

    def __init__(self, catalog: CatalogRepositoryInterface) -> None:
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
            lambda a: not a.has_description(),
        )
