from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.ports.governance_port import IGovernanceRepository


class SearchDataProductsUseCase:
    def __init__(self, governance: IGovernanceRepository) -> None:
        self._governance = governance

    async def execute(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
    ) -> list[DataProduct]:
        return await self._governance.search_data_products(query, limit, domain_id)
