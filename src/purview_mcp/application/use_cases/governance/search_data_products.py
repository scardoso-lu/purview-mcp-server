from purview_mcp.domain.entities.data_product import DataProduct
from purview_mcp.domain.repositories.interfaces import GovernanceRepositoryInterface
from purview_mcp.shared.observability import Logger


class SearchDataProductsUseCase:
    def __init__(self, governance: GovernanceRepositoryInterface, log: Logger) -> None:
        self._governance = governance
        self._log = log

    async def execute(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
        offset: int = 0,
    ) -> list[DataProduct]:
        result = await self._governance.search_data_products(query, limit, domain_id, offset=offset)
        self._log.info("governance.search_data_products.completed", query=query, count=len(result))
        return result
