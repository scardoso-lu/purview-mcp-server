from purview_mcp.domain.entities.lineage import LineageGraph
from purview_mcp.infrastructure.repositories.contract import LineageRepositoryInterface


class GetAssetLineageUseCase:
    def __init__(self, lineage: LineageRepositoryInterface) -> None:
        self._lineage = lineage

    async def execute(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        return await self._lineage.get_lineage(guid, direction, depth)
