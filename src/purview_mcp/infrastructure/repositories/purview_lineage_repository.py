from typing import Any

from purview_mcp.domain.models.lineage import LineageGraph, LineageRelation
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient

# Re-exported for backward compatibility (tests and the ETL import this).
from purview_mcp.infrastructure.repositories._parsers import _parse_node  # noqa: F401


class PurviewLineageRepository:
    def __init__(self, client: DataMapClient) -> None:
        self._client = client

    async def get_lineage(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        raw: Any = await self._client.get_lineage(guid, direction, depth)

        guid_entity_map: dict[str, dict[str, Any]] = raw.get("guidEntityMap", {})
        relations_raw: list[dict[str, Any]] = raw.get("relations", [])

        upstream_ids: set[str] = set()
        downstream_ids: set[str] = set()
        for rel in relations_raw:
            from_id = rel.get("fromEntityId", "")
            to_id = rel.get("toEntityId", "")
            if to_id == guid:
                upstream_ids.add(from_id)
            elif from_id == guid:
                downstream_ids.add(to_id)

        upstream_nodes = [
            _parse_node(guid_entity_map[uid]) for uid in upstream_ids if uid in guid_entity_map
        ]
        downstream_nodes = [
            _parse_node(guid_entity_map[did]) for did in downstream_ids if did in guid_entity_map
        ]
        relations = [
            LineageRelation(
                from_id=r.get("fromEntityId", ""),
                to_id=r.get("toEntityId", ""),
                relation_type=r.get("relationshipType"),
            )
            for r in relations_raw
        ]

        return LineageGraph(
            asset_id=guid,
            upstream=upstream_nodes,
            downstream=downstream_nodes,
            relations=relations,
        )
