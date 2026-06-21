from typing import Literal

from purview_mcp.domain.entities.lineage import LineageGraph
from purview_mcp.domain.repositories.interfaces import LineageRepositoryInterface
from purview_mcp.shared.observability import Logger


class GetAssetLineageUseCase:
    def __init__(self, lineage: LineageRepositoryInterface, log: Logger) -> None:
        self._lineage = lineage
        self._log = log

    async def execute(
        self,
        guid: str,
        direction: Literal["BOTH", "INPUT", "OUTPUT"] = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        result = await self._lineage.get_lineage(guid, direction, depth)
        self._log.info("lineage.get_asset_lineage.completed", guid=guid, direction=direction)
        return result
