from mcp.server.fastmcp import FastMCP

from purview_mcp.presentation.container import Container
from purview_mcp.presentation.mcp.tools import (
    find_authoritative_source,
    get_asset_details,
    get_asset_lineage,
    get_asset_owner,
    get_data_quality,
    search_assets,
    search_data_products,
    search_glossary_terms,
)


def create_server(container: Container) -> FastMCP:
    mcp = FastMCP(
        name="Microsoft Purview Unified Catalog",
        instructions=(
            "This server exposes Microsoft Purview governance metadata. "
            "Use search_assets to discover datasets, get_asset_lineage to trace data flow, "
            "find_authoritative_source to identify the most trusted dataset for a business concept, "
            "and search_glossary_terms to look up business definitions."
        ),
    )

    search_assets.register(mcp, container.search_assets)
    get_asset_details.register(mcp, container.get_asset_details)
    get_asset_lineage.register(mcp, container.get_asset_lineage)
    get_asset_owner.register(mcp, container.get_asset_owner)
    search_glossary_terms.register(mcp, container.search_glossary_terms)
    search_data_products.register(mcp, container.search_data_products)
    find_authoritative_source.register(mcp, container.find_authoritative_source)
    get_data_quality.register(mcp, container.get_data_quality)

    return mcp
