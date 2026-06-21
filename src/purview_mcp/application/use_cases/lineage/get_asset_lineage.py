from typing import Literal

from purview_mcp.domain.entities.lineage import LineageGraph
from purview_mcp.domain.repositories.interfaces import LineageRepositoryInterface


class GetAssetLineageUseCase:
    def __init__(self, lineage: LineageRepositoryInterface) -> None:
        self._lineage = lineage

    async def execute(
        self,
        guid: str,
        direction: Literal["BOTH", "INPUT", "OUTPUT"] = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        return await self._lineage.get_lineage(guid, direction, depth)
