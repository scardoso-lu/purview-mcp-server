from typing import Protocol

from purview_mcp.domain.models.lineage import LineageGraph


class ILineageRepository(Protocol):
    async def get_lineage(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> LineageGraph: ...
