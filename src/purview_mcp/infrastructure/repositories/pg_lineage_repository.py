"""Postgres-backed lineage repository (implements ILineageRepository).

Walks the cached ``lineage_relations`` edge set out to ``depth`` hops and
reproduces the live repo's semantics: only *direct* neighbours of the asset are
classified into upstream/downstream, while ``relations`` holds every edge in the
traversed sub-graph.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purview_mcp.domain.models.lineage import LineageGraph, LineageNode, LineageRelation
from purview_mcp.infrastructure.db import models as m


class PgLineageRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def get_lineage(
        self,
        guid: str,
        direction: str = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        direction = direction.upper()
        async with self._sm() as session:
            visited: set[str] = {guid}
            frontier: set[str] = {guid}
            edges: dict[tuple[str, str, str], m.LineageRelation] = {}

            for _ in range(max(1, depth)):
                if not frontier:
                    break
                conds = []
                if direction in ("BOTH", "OUTPUT"):
                    conds.append(m.LineageRelation.from_id.in_(frontier))
                if direction in ("BOTH", "INPUT"):
                    conds.append(m.LineageRelation.to_id.in_(frontier))
                result = await session.execute(select(m.LineageRelation).where(or_(*conds)))
                rows = result.scalars().all()
                new_frontier: set[str] = set()
                for r in rows:
                    edges[(r.from_id, r.to_id, r.relation_type or "")] = r
                    for neighbor in (r.from_id, r.to_id):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            new_frontier.add(neighbor)
                frontier = new_frontier

            # Direct-neighbour classification (matches the live repo).
            upstream_ids = {r.from_id for r in edges.values() if r.to_id == guid}
            downstream_ids = {r.to_id for r in edges.values() if r.from_id == guid}

            node_ids = upstream_ids | downstream_ids
            nodes_by_id: dict[str, m.LineageNode] = {}
            if node_ids:
                node_result = await session.execute(
                    select(m.LineageNode).where(m.LineageNode.id.in_(node_ids))
                )
                nodes_by_id = {n.id: n for n in node_result.scalars().all()}

        def _node(node_id: str) -> LineageNode:
            n = nodes_by_id.get(node_id)
            if n is None:
                return LineageNode(id=node_id, name="", asset_type="", qualified_name="")
            return LineageNode(
                id=n.id, name=n.name, asset_type=n.asset_type, qualified_name=n.qualified_name
            )

        return LineageGraph(
            asset_id=guid,
            upstream=[_node(i) for i in upstream_ids],
            downstream=[_node(i) for i in downstream_ids],
            relations=[
                LineageRelation(from_id=r.from_id, to_id=r.to_id, relation_type=r.relation_type)
                for r in edges.values()
            ],
        )
