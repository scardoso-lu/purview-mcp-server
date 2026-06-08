from purview_mcp.domain.models.asset import Asset, AssetOwner
from purview_mcp.domain.models.lineage import LineageGraph, LineageNode


def test_asset_model_defaults() -> None:
    asset = Asset(id="x", name="Test", asset_type="table", qualified_name="q")
    assert asset.owners == []
    assert asset.classification == []
    assert asset.tags == []
    assert asset.endorsement is None
    assert asset.description is None


def test_asset_owner_fields() -> None:
    owner = AssetOwner(id="u1", display_name="Alice", contact_type="Owner")
    assert owner.email is None


def test_lineage_graph_empty_by_default() -> None:
    graph = LineageGraph(asset_id="guid-1")
    assert graph.upstream == []
    assert graph.downstream == []
    assert graph.relations == []


def test_lineage_node_model() -> None:
    node = LineageNode(id="n1", name="Source", asset_type="table", qualified_name="q")
    data = node.model_dump()
    assert data["id"] == "n1"
    assert data["asset_type"] == "table"
