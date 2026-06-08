from purview_mcp.domain.models.lineage import LineageGraph
from purview_mcp.domain.ports.lineage_port import ILineageRepository


class GetAssetLineageUseCase:
    def __init__(self, lineage: ILineageRepository) -> None:
        self._lineage = lineage

    async def execute(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        return await self._lineage.get_lineage(guid, direction, depth)
