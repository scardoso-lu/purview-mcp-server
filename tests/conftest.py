from unittest.mock import MagicMock

import pytest

from purview_mcp.domain.entities.asset import Asset, AssetOwner
from purview_mcp.domain.entities.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.entities.glossary import GlossaryTerm
from purview_mcp.domain.entities.lineage import LineageGraph, LineageNode
from purview_mcp.shared.observability import Logger


@pytest.fixture
def logger() -> Logger:
    return MagicMock(spec=Logger)  # type: ignore[return-value]


@pytest.fixture
def certified_asset() -> Asset:
    return Asset._mock(
        id="guid-certified",
        name="Customer Master Table",
        description="The authoritative customer master record.",
        owners=[AssetOwner._mock(id="u1", display_name="Alice", contact_type="Owner")],
        classification=["MICROSOFT.PERSONAL.EMAIL"],
        endorsement="Certified",
        domain="Sales",
        tags=["core", "crm"],
        qualified_name="mssql://server/db/dbo/customers",
    )


@pytest.fixture
def uncertified_asset() -> Asset:
    return Asset._mock(
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
    return Asset._mock(
        id="guid-promoted",
        name="Customer Summary",
        description="Aggregated customer stats.",
        owners=[AssetOwner._mock(id="u2", display_name="Bob", contact_type="Expert")],
        classification=[],
        endorsement="Promoted",
        domain="Marketing",
        tags=[],
        qualified_name="mssql://server/db/dbo/customer_summary",
    )


@pytest.fixture
def sample_glossary_term() -> GlossaryTerm:
    return GlossaryTerm._mock(
        id="term-1",
        name="Customer",
        qualified_name="Glossary.Customer",
        definition="An individual or organization that purchases products or services.",
        status="Approved",
        synonyms=["Client", "Account"],
    )


@pytest.fixture
def sample_data_product() -> DataProduct:
    return DataProduct._mock(
        id="dp-1",
        name="Sales Data Product",
        description="Governed sales data.",
        status="Active",
        owners=[DataProductOwner._mock(id="u3", display_name="Carol")],
        domain_id="domain-sales",
        domain_name="Sales",
    )


@pytest.fixture
def sample_lineage_graph() -> LineageGraph:
    return LineageGraph._mock(
        asset_id="guid-certified",
        upstream=[
            LineageNode._mock(
                id="src-1", name="SAP Orders", asset_type="sap_table", qualified_name="sap://orders"
            )
        ],
        downstream=[
            LineageNode._mock(
                id="pbi-1",
                name="Sales Dashboard",
                asset_type="PowerBIDataset",
                qualified_name="pbi://sales",
            )
        ],
    )
