from collections.abc import Callable

from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository

# Purview's search filter cannot express "has a description", so documented /
# undocumented filtering happens client-side: raw result pages are fetched and
# filtered until the requested filtered page is filled or the server runs out
# of results. _MAX_RAW_SCAN bounds the total raw results examined per request.
_MAX_PAGE_SIZE = 1000  # Purview search API maximum page size
_MAX_RAW_SCAN = 10_000


async def search_assets_filtered(
    catalog: ICatalogRepository,
    query: str,
    limit: int,
    asset_type: str | None,
    classification: str | None,
    offset: int,
    predicate: Callable[[Asset], bool],
) -> list[Asset]:
    """Return the filtered page [offset : offset + limit] of matching assets."""
    needed = offset + limit
    page_size = min(max(needed * 2, 50), _MAX_PAGE_SIZE)
    matched: list[Asset] = []
    raw_offset = 0
    while len(matched) < needed and raw_offset < _MAX_RAW_SCAN:
        page = await catalog.search_assets(
            query, page_size, asset_type, classification, offset=raw_offset
        )
        matched.extend(a for a in page if predicate(a))
        if len(page) < page_size:
            break  # server results exhausted
        raw_offset += page_size
    return matched[offset : offset + limit]
