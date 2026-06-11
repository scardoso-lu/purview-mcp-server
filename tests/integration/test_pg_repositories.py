import pytest

from purview_mcp.domain.exceptions import AssetNotFoundError
from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.domain.models.data_product import DataProduct
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageNode, LineageRelation
from purview_mcp.infrastructure.etl.load import AssetRecord, Loader
from purview_mcp.infrastructure.repositories.pg_catalog_repository import PgCatalogRepository
from purview_mcp.infrastructure.repositories.pg_governance_repository import PgGovernanceRepository
from purview_mcp.infrastructure.repositories.pg_lineage_repository import PgLineageRepository

pytestmark = pytest.mark.asyncio


def _asset(guid: str, name: str, desc: str | None, **kw) -> AssetRecord:  # noqa: ANN003
    return AssetRecord(
        asset=Asset(
            id=guid,
            name=name,
            asset_type=kw.get("asset_type", "azure_sql_table"),
            description=desc,
            qualified_name=f"qn://{guid}",
            owners=kw.get("owners", []),
            classification=kw.get("classification", []),
            tags=kw.get("tags", []),
            data_quality=kw.get("data_quality", []),
        ),
        update_time=kw.get("update_time", 1),
    )


async def _seed_assets(sessionmaker, records) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run = await loader.start_run("full")
    await loader.upsert_assets(run, records)


async def test_search_assets_keyword_and_filters(sessionmaker) -> None:  # noqa: ANN001
    await _seed_assets(
        sessionmaker,
        [
            _asset("g1", "Customer Orders", "all customer orders", classification=["PII"]),
            _asset("g2", "Inventory", "warehouse stock levels"),
            _asset("g3", "Customer Profile", "customer master data", asset_type="PowerBIDataset"),
        ],
    )
    repo = PgCatalogRepository(sessionmaker)

    hits = await repo.search_assets("customer", limit=10)
    assert {a.id for a in hits} == {"g1", "g3"}

    typed = await repo.search_assets("customer", limit=10, asset_type="PowerBIDataset")
    assert {a.id for a in typed} == {"g3"}

    classified = await repo.search_assets("customer", limit=10, classification="PII")
    assert {a.id for a in classified} == {"g1"}


async def test_search_assets_omits_data_quality(sessionmaker) -> None:  # noqa: ANN001
    await _seed_assets(
        sessionmaker,
        [
            _asset(
                "g1",
                "Orders",
                "orders",
                owners=[AssetOwner(id="u", display_name="A", contact_type="Owner")],
                data_quality=[DataQualityMetric(name="completeness", value=0.9)],
            )
        ],
    )
    repo = PgCatalogRepository(sessionmaker)

    [hit] = await repo.search_assets("orders", limit=10)
    # Light projection: owners present, data quality omitted (parity with live).
    assert hit.owners and hit.owners[0].id == "u"
    assert hit.data_quality == []


async def test_get_asset_by_id_full_shape(sessionmaker) -> None:  # noqa: ANN001
    await _seed_assets(
        sessionmaker,
        [
            _asset(
                "g1",
                "Orders",
                "orders",
                data_quality=[DataQualityMetric(name="completeness", value=0.9, status="ok")],
            )
        ],
    )
    repo = PgCatalogRepository(sessionmaker)

    asset = await repo.get_asset_by_id("g1")
    assert asset.id == "g1"
    assert asset.data_quality and asset.data_quality[0].name == "completeness"

    with pytest.raises(AssetNotFoundError):
        await repo.get_asset_by_id("missing")


async def test_governance_glossary_and_data_products(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run = await loader.start_run("full")
    await loader.upsert_glossary_terms(
        run,
        [
            GlossaryTerm(id="t1", name="Customer Churn", qualified_name="q", definition="leaving"),
            GlossaryTerm(id="t2", name="Revenue", qualified_name="q", definition="money"),
        ],
    )
    await loader.upsert_data_products(
        run,
        [
            DataProduct(id="dp1", name="Sales Mart", domain_id="d1"),
            DataProduct(id="dp2", name="HR Mart", domain_id="d2"),
        ],
    )
    repo = PgGovernanceRepository(sessionmaker)

    terms = await repo.search_glossary_terms("churn", limit=10)
    assert {t.id for t in terms} == {"t1"}

    products = await repo.search_data_products("mart", limit=10)
    assert {p.id for p in products} == {"dp1", "dp2"}

    scoped = await repo.search_data_products("mart", limit=10, domain_id="d1")
    assert {p.id for p in scoped} == {"dp1"}


async def test_lineage_upstream_downstream_classification(sessionmaker) -> None:  # noqa: ANN001
    loader = Loader(sessionmaker)
    run = await loader.start_run("full")
    nodes = [
        LineageNode(id="up", name="Up", asset_type="t", qualified_name="qu"),
        LineageNode(id="me", name="Me", asset_type="t", qualified_name="qm"),
        LineageNode(id="down", name="Down", asset_type="t", qualified_name="qd"),
    ]
    relations = [
        LineageRelation(from_id="up", to_id="me", relation_type="dataflow"),
        LineageRelation(from_id="me", to_id="down", relation_type="dataflow"),
    ]
    await loader.upsert_lineage(run, nodes, relations)
    repo = PgLineageRepository(sessionmaker)

    graph = await repo.get_lineage("me", "BOTH", depth=3)
    assert {n.id for n in graph.upstream} == {"up"}
    assert {n.id for n in graph.downstream} == {"down"}
    assert len(graph.relations) == 2

    # Direction filter: only upstream edges.
    up_only = await repo.get_lineage("me", "INPUT", depth=3)
    assert {n.id for n in up_only.upstream} == {"up"}
    assert up_only.downstream == []
