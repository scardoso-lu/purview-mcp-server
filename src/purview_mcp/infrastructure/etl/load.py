"""Load layer: upsert extracted Purview data into Postgres and reconcile deletes.

All writes go through SQLAlchemy. Bulk upserts use the Postgres dialect's
``INSERT ... ON CONFLICT DO UPDATE``; child collections (owners, classifications,
tags, data-quality metrics, data-product owners) are delete-then-insert per
parent within the batch transaction. The ``last_seen_run_id`` stamp drives
delete detection during a full reconcile.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TypeVar

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageNode as DomainLineageNode
from purview_mcp.domain.models.lineage import LineageRelation as DomainLineageRelation
from purview_mcp.infrastructure.db import models as m

logger = structlog.get_logger(__name__)

T = TypeVar("T")


@dataclass
class AssetRecord:
    """A fully-extracted asset plus the fields that live outside the domain model."""

    asset: Asset
    update_time: int | None = None
    raw_attributes: dict[str, Any] | None = None


@dataclass
class RunCounts:
    assets_upserted: int = 0
    terms_upserted: int = 0
    products_upserted: int = 0
    deletes: int = 0
    high_watermark: int | None = None
    errors: list[str] = field(default_factory=list)


def _chunk(items: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


class Loader:
    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], batch_size: int = 500
    ) -> None:
        self._sm = sessionmaker
        self._batch_size = batch_size

    # --- run lifecycle -------------------------------------------------------

    async def start_run(self, kind: str) -> int:
        async with self._sm.begin() as session:
            result = await session.execute(
                pg_insert(m.EtlRun).values(kind=kind, status="running").returning(m.EtlRun.run_id)
            )
            return int(result.scalar_one())

    async def finish_run(
        self,
        run_id: int,
        status: str,
        counts: RunCounts | None = None,
        error: str | None = None,
    ) -> None:
        counts = counts or RunCounts()
        async with self._sm.begin() as session:
            run = await session.get(m.EtlRun, run_id)
            if run is None:
                return
            run.status = status
            run.finished_at = datetime.now(timezone.utc)
            run.assets_upserted = counts.assets_upserted
            run.terms_upserted = counts.terms_upserted
            run.products_upserted = counts.products_upserted
            run.deletes = counts.deletes
            run.high_watermark = counts.high_watermark
            run.error = error

    # --- state queries -------------------------------------------------------

    async def last_high_watermark(self) -> int | None:
        async with self._sm() as session:
            result = await session.execute(
                select(func.max(m.EtlRun.high_watermark)).where(m.EtlRun.status == "success")
            )
            value = result.scalar_one_or_none()
            return int(value) if value is not None else None

    async def asset_count(self) -> int:
        async with self._sm() as session:
            result = await session.execute(select(func.count()).select_from(m.Asset))
            return int(result.scalar_one())

    async def has_successful_run(self) -> bool:
        async with self._sm() as session:
            result = await session.execute(
                select(func.count()).select_from(m.EtlRun).where(m.EtlRun.status == "success")
            )
            return int(result.scalar_one()) > 0

    # --- upserts -------------------------------------------------------------

    async def upsert_assets(self, run_id: int, records: Sequence[AssetRecord]) -> int:
        total = 0
        for batch in _chunk(records, self._batch_size):
            async with self._sm.begin() as session:
                asset_rows = [self._asset_row(r, run_id) for r in batch]
                await self._upsert(session, m.Asset, asset_rows, ["id"])

                ids = [r.asset.id for r in batch]
                await session.execute(delete(m.AssetOwner).where(m.AssetOwner.asset_id.in_(ids)))
                await session.execute(
                    delete(m.Classification).where(m.Classification.asset_id.in_(ids))
                )
                await session.execute(delete(m.Tag).where(m.Tag.asset_id.in_(ids)))
                await session.execute(
                    delete(m.DataQualityMetric).where(m.DataQualityMetric.asset_id.in_(ids))
                )

                owner_rows: list[dict[str, Any]] = []
                class_rows: list[dict[str, Any]] = []
                tag_rows: list[dict[str, Any]] = []
                dq_rows: list[dict[str, Any]] = []
                for r in batch:
                    a = r.asset
                    seen_owner: set[tuple[str, str]] = set()
                    for o in a.owners:
                        key = (o.id, o.contact_type)
                        if key in seen_owner:
                            continue
                        seen_owner.add(key)
                        owner_rows.append(
                            {
                                "asset_id": a.id,
                                "owner_id": o.id,
                                "contact_type": o.contact_type,
                                "display_name": o.display_name,
                                "email": o.email,
                            }
                        )
                    for c in dict.fromkeys(a.classification):
                        class_rows.append({"asset_id": a.id, "classification": c})
                    for t in dict.fromkeys(a.tags):
                        tag_rows.append({"asset_id": a.id, "tag": t})
                    seen_dq: set[str] = set()
                    for dq in a.data_quality:
                        if dq.name in seen_dq:
                            continue
                        seen_dq.add(dq.name)
                        dq_rows.append(
                            {
                                "asset_id": a.id,
                                "name": dq.name,
                                "value": dq.value,
                                "status": dq.status,
                            }
                        )
                if owner_rows:
                    await session.execute(pg_insert(m.AssetOwner), owner_rows)
                if class_rows:
                    await session.execute(pg_insert(m.Classification), class_rows)
                if tag_rows:
                    await session.execute(pg_insert(m.Tag), tag_rows)
                if dq_rows:
                    await session.execute(pg_insert(m.DataQualityMetric), dq_rows)
            total += len(batch)
        return total

    async def upsert_glossary_terms(self, run_id: int, terms: Sequence[GlossaryTerm]) -> int:
        total = 0
        for batch in _chunk(terms, self._batch_size):
            rows = [
                {
                    "id": t.id,
                    "name": t.name,
                    "qualified_name": t.qualified_name,
                    "definition": t.definition,
                    "status": t.status,
                    "long_description": t.long_description,
                    "examples": list(t.examples),
                    "synonyms": list(t.synonyms),
                    "stewards": list(t.stewards),
                    "experts": list(t.experts),
                    "last_seen_run_id": run_id,
                }
                for t in batch
            ]
            async with self._sm.begin() as session:
                await self._upsert(session, m.GlossaryTerm, rows, ["id"])
            total += len(batch)
        return total

    async def upsert_data_products(self, run_id: int, products: Sequence[DataProduct]) -> int:
        total = 0
        for batch in _chunk(products, self._batch_size):
            async with self._sm.begin() as session:
                rows = [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "status": p.status,
                        "domain_id": p.domain_id,
                        "domain_name": p.domain_name,
                        "asset_count": p.asset_count,
                        "data_product_type": p.data_product_type,
                        "tags": list(p.tags),
                        "last_seen_run_id": run_id,
                    }
                    for p in batch
                ]
                await self._upsert(session, m.DataProduct, rows, ["id"])

                ids = [p.id for p in batch]
                await session.execute(
                    delete(m.DataProductOwner).where(m.DataProductOwner.data_product_id.in_(ids))
                )
                owner_rows: list[dict[str, Any]] = []
                for p in batch:
                    seen: set[str] = set()
                    for o in p.owners:
                        if o.id in seen:
                            continue
                        seen.add(o.id)
                        owner_rows.append(
                            {
                                "data_product_id": p.id,
                                "owner_id": o.id,
                                "display_name": o.display_name,
                                "email": o.email,
                            }
                        )
                if owner_rows:
                    await session.execute(pg_insert(m.DataProductOwner), owner_rows)
            total += len(batch)
        return total

    async def upsert_lineage(
        self,
        run_id: int,
        nodes: Sequence[DomainLineageNode],
        relations: Sequence[DomainLineageRelation],
    ) -> None:
        # Dedupe nodes by id: shared upstream/downstream nodes recur across
        # per-asset lineage graphs, and a single INSERT ... ON CONFLICT DO UPDATE
        # cannot touch the same primary key twice. Last occurrence wins.
        node_by_id: dict[str, dict[str, Any]] = {}
        for n in nodes:
            if not n.id:
                continue
            node_by_id[n.id] = {
                "id": n.id,
                "name": n.name,
                "asset_type": n.asset_type,
                "qualified_name": n.qualified_name,
                "last_seen_run_id": run_id,
            }
        node_rows = list(node_by_id.values())
        for batch in _chunk(node_rows, self._batch_size):
            async with self._sm.begin() as session:
                await self._upsert(session, m.LineageNode, list(batch), ["id"])

        # Dedupe relations on (from_id, to_id, rel_type_key) to satisfy the
        # unique constraint within a single statement.
        seen_rel: set[tuple[str, str, str]] = set()
        rel_rows: list[dict[str, Any]] = []
        for r in relations:
            if not r.from_id or not r.to_id:
                continue
            key = (r.from_id, r.to_id, r.relation_type or "")
            if key in seen_rel:
                continue
            seen_rel.add(key)
            rel_rows.append(
                {
                    "from_id": r.from_id,
                    "to_id": r.to_id,
                    "relation_type": r.relation_type,
                    "last_seen_run_id": run_id,
                }
            )
        for batch in _chunk(rel_rows, self._batch_size):
            async with self._sm.begin() as session:
                stmt = pg_insert(m.LineageRelation).values(list(batch))
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_lineage_relation",
                    set_={"last_seen_run_id": stmt.excluded.last_seen_run_id},
                )
                await session.execute(stmt)

    # --- delete reconcile ----------------------------------------------------

    async def reconcile_deletes(self, run_id: int) -> int:
        """Delete rows not seen in run ``run_id`` (full reconcile only)."""
        deleted = 0
        async with self._sm.begin() as session:
            for model in (
                m.Asset,
                m.GlossaryTerm,
                m.DataProduct,
                m.LineageNode,
                m.LineageRelation,
            ):
                result = await session.execute(delete(model).where(model.last_seen_run_id < run_id))
                deleted += getattr(result, "rowcount", 0) or 0
        return deleted

    # --- helpers -------------------------------------------------------------

    def _asset_row(self, record: AssetRecord, run_id: int) -> dict[str, Any]:
        a = record.asset
        return {
            "id": a.id,
            "name": a.name,
            "asset_type": a.asset_type,
            "description": a.description,
            "endorsement": a.endorsement,
            "domain": a.domain,
            "qualified_name": a.qualified_name,
            "collection": a.collection,
            "update_time": record.update_time,
            "raw_attributes": record.raw_attributes,
            "extracted_at": datetime.now(timezone.utc),
            "last_seen_run_id": run_id,
        }

    @staticmethod
    async def _upsert(
        session: AsyncSession,
        model: type[m.Base],
        rows: list[dict[str, Any]],
        conflict: list[str],
    ) -> None:
        if not rows:
            return
        stmt = pg_insert(model).values(rows)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in model.__table__.columns
            if c.name not in conflict and c.computed is None and c.name != "extracted_at"
        }
        if update_cols:
            stmt = stmt.on_conflict_do_update(index_elements=conflict, set_=update_cols)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict)
        await session.execute(stmt)
