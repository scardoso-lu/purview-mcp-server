from purview_mcp.domain.entities.data_product import DataProduct
from purview_mcp.domain.repositories.interfaces import GovernanceRepositoryInterface


class SearchDataProductsUseCase:
    def __init__(self, governance: GovernanceRepositoryInterface) -> None:
        self._governance = governance

    async def execute(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
        offset: int = 0,
    ) -> list[DataProduct]:
        return await self._governance.search_data_products(query, limit, domain_id, offset=offset)
