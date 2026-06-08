import pytest

from purview_mcp.domain.models.asset import Asset, AssetOwner
from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageGraph, LineageNode


@pytest.fixture
def certified_asset() -> Asset:
    return Asset(
        id="guid-certified",
        name="Customer Master Table",
        asset_type="azure_sql_table",
        description="The authoritative customer master record.",
        owners=[AssetOwner(id="u1", display_name="Alice", contact_type="Owner")],
        classification=["MICROSOFT.PERSONAL.EMAIL"],
        endorsement="Certified",
        domain="Sales",
        tags=["core", "crm"],
        qualified_name="mssql://server/db/dbo/customers",
    )


@pytest.fixture
def uncertified_asset() -> Asset:
    return Asset(
        id="guid-uncertified",
        name="Customer Temp View",
        asset_type="azure_sql_view",
        description=None,
        owners=[],
        classification=[],
        endorsement=None,
        domain=None,
        tags=[],
        qualified_name="mssql://server/db/dbo/vw_customers_temp",
    )


@pytest.fixture
def promoted_asset() -> Asset:
    return Asset(
        id="guid-promoted",
        name="Customer Summary",
        asset_type="azure_sql_table",
        description="Aggregated customer stats.",
        owners=[AssetOwner(id="u2", display_name="Bob", contact_type="Expert")],
        classification=[],
        endorsement="Promoted",
        domain="Marketing",
        tags=[],
        qualified_name="mssql://server/db/dbo/customer_summary",
    )


@pytest.fixture
def sample_glossary_term() -> GlossaryTerm:
    return GlossaryTerm(
        id="term-1",
        name="Customer",
        qualified_name="Glossary.Customer",
        definition="An individual or organization that purchases products or services.",
        status="Approved",
        synonyms=["Client", "Account"],
    )


@pytest.fixture
def sample_data_product() -> DataProduct:
    return DataProduct(
        id="dp-1",
        name="Sales Data Product",
        description="Governed sales data.",
        status="Active",
        owners=[DataProductOwner(id="u3", display_name="Carol")],
        domain_id="domain-sales",
        domain_name="Sales",
    )


@pytest.fixture
def sample_lineage_graph() -> LineageGraph:
    return LineageGraph(
        asset_id="guid-certified",
        upstream=[
            LineageNode(
                id="src-1", name="SAP Orders", asset_type="sap_table", qualified_name="sap://orders"
            )
        ],
        downstream=[
            LineageNode(
                id="pbi-1",
                name="Sales Dashboard",
                asset_type="PowerBIDataset",
                qualified_name="pbi://sales",
            )
        ],
    )
