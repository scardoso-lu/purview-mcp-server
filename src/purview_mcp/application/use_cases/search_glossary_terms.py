from purview_mcp.domain.entities.glossary import GlossaryTerm
from purview_mcp.infrastructure.repositories.contract import GovernanceRepositoryInterface


class SearchGlossaryTermsUseCase:
    def __init__(self, governance: GovernanceRepositoryInterface) -> None:
        self._governance = governance

    async def execute(self, query: str, limit: int = 25, offset: int = 0) -> list[GlossaryTerm]:
        return await self._governance.search_glossary_terms(query, limit, offset=offset)
