from typing import Protocol

from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.models.glossary import GlossaryTerm


class IGovernanceRepository(Protocol):
    async def search_glossary_terms(
        self,
        query: str,
        limit: int = 25,
    ) -> list[GlossaryTerm]: ...

    async def search_data_products(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
    ) -> list[DataProduct]: ...
