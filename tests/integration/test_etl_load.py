import pytest
from sqlalchemy import func, select

from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageNode, LineageRelation
from purview_mcp.infrastructure.db import models as m
from purview_mcp.infrastructure.etl.load import AssetRecord, Loader

pytestmark = pytest.mark.asyncio


def _asset(guid: str, name: str = "Orders", *, dq: bool = False) -> AssetRecord:
    return AssetRecord(
        asset=Asset(
            id=guid,
            name=name,
            asset_type="azure_sql_table",
            description="customer orders",
            qualified_name=f"qn://{guid}",
            owners=[AssetOwner(id="u1", display_name="Ann", contact_type="Owner", email="a@x.io")],
            classification=["MICROSOFT.PERSONAL.EMAIL"],
            tags=["gold"],
            data_quality=[DataQualityMetric(name="completeness", value=0.9)] if dq else [],
        ),
        update_time=100,
        raw_attributes={"qualifiedName": f"qn://{guid}"},
    )


async def _count(sm, model) -> int:  # noqa: ANN001
    async with sm() as session:
        return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


async def test_upsert_assets_is_idempotent(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run1 = await loader.start_run("full")
    await loader.upsert_assets(run1, [_asset("g1")])
    run2 = await loader.start_run("full")
    await loader.upsert_assets(run2, [_asset("g1", name="Orders v2")])

    assert await _count(sessionmaker, m.Asset) == 1
    # Child rows are replaced, not duplicated.
    assert await _count(sessionmaker, m.AssetOwner) == 1
    assert await _count(sessionmaker, m.Classification) == 1
    async with sessionmaker() as session:
        row = await session.get(m.Asset, "g1")
        assert row.name == "Orders v2"
        assert row.last_seen_run_id == run2


async def test_full_reconcile_deletes_vanished_rows(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run1 = await loader.start_run("full")
    await loader.upsert_assets(run1, [_asset("g1"), _asset("g2")])

    run2 = await loader.start_run("full")
    await loader.upsert_assets(run2, [_asset("g1")])
    deleted = await loader.reconcile_deletes(run2)

    assert deleted == 1
    assert await _count(sessionmaker, m.Asset) == 1
    async with sessionmaker() as session:
        assert await session.get(m.Asset, "g2") is None


async def test_upsert_glossary_and_data_products(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run = await loader.start_run("full")
    n_terms = await loader.upsert_glossary_terms(
        run, [GlossaryTerm(id="t1", name="Churn", qualified_name="qn", synonyms=["attrition"])]
    )
    n_products = await loader.upsert_data_products(
        run,
        [
            DataProduct(
                id="dp1",
                name="Sales",
                owners=[DataProductOwner(id="o1", display_name="Bob")],
            )
        ],
    )

    assert (n_terms, n_products) == (1, 1)
    assert await _count(sessionmaker, m.DataProductOwner) == 1
    async with sessionmaker() as session:
        term = await session.get(m.GlossaryTerm, "t1")
        assert term.synonyms == ["attrition"]


async def test_upsert_lineage_dedupes_relations(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run = await loader.start_run("full")
    nodes = [
        LineageNode(id="a", name="A", asset_type="t", qualified_name="qa"),
        LineageNode(id="b", name="B", asset_type="t", qualified_name="qb"),
        # Duplicate node id (shared across per-asset lineage graphs); must not
        # crash the single ON CONFLICT upsert, and last occurrence wins.
        LineageNode(id="a", name="A2", asset_type="t", qualified_name="qa"),
    ]
    relations = [
        LineageRelation(from_id="a", to_id="b", relation_type="x"),
        LineageRelation(from_id="a", to_id="b", relation_type="x"),  # duplicate
    ]
    await loader.upsert_lineage(run, nodes, relations)

    assert await _count(sessionmaker, m.LineageNode) == 2
    assert await _count(sessionmaker, m.LineageRelation) == 1
    async with sessionmaker() as session:
        node = await session.get(m.LineageNode, "a")
        assert node.name == "A2"  # last write wins


async def test_watermark_tracks_successful_runs(sessionmaker) -> None:  # noqa: ANN001
    from purview_mcp.infrastructure.etl.load import RunCounts

    loader = Loader(sessionmaker)
    run = await loader.start_run("incremental")
    await loader.finish_run(run, "success", RunCounts(high_watermark=500))

    assert await loader.last_high_watermark() == 500
    assert await loader.has_successful_run() is True
