"""Postgres-backed governance repository (implements IGovernanceRepository)."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.infrastructure.db import models as m


class PgGovernanceRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def search_glossary_terms(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
    ) -> list[GlossaryTerm]:
        stmt = select(m.GlossaryTerm)
        if query:
            tsq = func.websearch_to_tsquery("simple", query)
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    m.GlossaryTerm.search_doc.op("@@")(tsq),
                    m.GlossaryTerm.name.ilike(like),
                    m.GlossaryTerm.definition.ilike(like),
                )
            )
        stmt = stmt.order_by(m.GlossaryTerm.name).limit(limit).offset(offset)

        async with self._sm() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [
            GlossaryTerm(
                id=t.id,
                name=t.name,
                qualified_name=t.qualified_name,
                definition=t.definition,
                status=t.status,
                long_description=t.long_description,
                examples=list(t.examples or []),
                synonyms=list(t.synonyms or []),
                stewards=list(t.stewards or []),
                experts=list(t.experts or []),
            )
            for t in rows
        ]

    async def search_data_products(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
        offset: int = 0,
    ) -> list[DataProduct]:
        stmt = select(m.DataProduct)
        if query:
            stmt = stmt.where(m.DataProduct.name.ilike(f"%{query}%"))
        if domain_id:
            stmt = stmt.where(m.DataProduct.domain_id == domain_id)
        stmt = stmt.order_by(m.DataProduct.name).limit(limit).offset(offset)

        async with self._sm() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [
            DataProduct(
                id=p.id,
                name=p.name,
                description=p.description,
                status=p.status,
                owners=[
                    DataProductOwner(id=o.owner_id, display_name=o.display_name, email=o.email)
                    for o in p.owners
                ],
                domain_id=p.domain_id,
                domain_name=p.domain_name,
                asset_count=p.asset_count,
                tags=list(p.tags or []),
                data_product_type=p.data_product_type,
            )
            for p in rows
        ]
