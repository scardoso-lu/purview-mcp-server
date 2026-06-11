"""Postgres-backed catalog repository (implements ICatalogRepository).

Reproduces the live Purview behaviour: ``search_assets`` returns the light
search projection (owners/classification/tags, but no data-quality, matching
``_parse_search_result``); ``get_asset_by_id`` returns the full record
(matching ``_parse_asset``).
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purview_mcp.domain.exceptions import AssetNotFoundError
from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.infrastructure.db import models as m


def _to_owner(o: m.AssetOwner) -> AssetOwner:
    return AssetOwner(
        id=o.owner_id,
        display_name=o.display_name,
        contact_type=o.contact_type,
        email=o.email,
    )


def _to_asset(row: m.Asset, *, include_data_quality: bool) -> Asset:
    return Asset(
        id=row.id,
        name=row.name,
        asset_type=row.asset_type,
        description=row.description,
        owners=[_to_owner(o) for o in row.owners],
        classification=[c.classification for c in row.classifications],
        endorsement=row.endorsement,
        domain=row.domain,
        tags=[t.tag for t in row.tags],
        qualified_name=row.qualified_name,
        collection=row.collection,
        data_quality=(
            [DataQualityMetric(name=d.name, value=d.value, status=d.status) for d in row.data_quality]
            if include_data_quality
            else []
        ),
    )


class PgCatalogRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def search_assets(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
        offset: int = 0,
    ) -> list[Asset]:
        stmt = select(m.Asset)
        if query:
            tsq = func.websearch_to_tsquery("simple", query)
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    m.Asset.search_doc.op("@@")(tsq),
                    m.Asset.name.ilike(like),
                    m.Asset.description.ilike(like),
                )
            ).order_by(func.ts_rank(m.Asset.search_doc, tsq).desc(), m.Asset.name)
        else:
            stmt = stmt.order_by(m.Asset.name)
        if asset_type:
            stmt = stmt.where(m.Asset.asset_type == asset_type)
        if classification:
            stmt = stmt.where(
                m.Asset.classifications.any(m.Classification.classification == classification)
            )
        stmt = stmt.limit(limit).offset(offset)

        async with self._sm() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [_to_asset(r, include_data_quality=False) for r in rows]

    async def get_asset_by_id(self, guid: str) -> Asset:
        async with self._sm() as session:
            row = await session.get(m.Asset, guid)
        if row is None:
            raise AssetNotFoundError(guid)
        return _to_asset(row, include_data_quality=True)
