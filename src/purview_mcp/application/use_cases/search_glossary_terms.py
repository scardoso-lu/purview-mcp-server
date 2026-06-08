from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.ports.governance_port import IGovernanceRepository


class SearchGlossaryTermsUseCase:
    def __init__(self, governance: IGovernanceRepository) -> None:
        self._governance = governance

    async def execute(self, query: str, limit: int = 25) -> list[GlossaryTerm]:
        return await self._governance.search_glossary_terms(query, limit)
