from purview_mcp.domain.entities.glossary import GlossaryTerm
from purview_mcp.domain.repositories.interfaces import GovernanceRepositoryInterface
from purview_mcp.shared.observability import Logger


class SearchGlossaryTermsUseCase:
    def __init__(self, governance: GovernanceRepositoryInterface, log: Logger) -> None:
        self._governance = governance
        self._log = log

    async def execute(self, query: str, limit: int = 25, offset: int = 0) -> list[GlossaryTerm]:
        result = await self._governance.search_glossary_terms(query, limit, offset=offset)
        self._log.info("governance.search_glossary_terms.completed", query=query, count=len(result))
        return result
