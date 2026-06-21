from collections.abc import Callable

from purview_mcp.domain.entities.asset import Asset
from purview_mcp.infrastructure.repositories.contract import CatalogRepositoryInterface

# ponytail: client-side description filter — Purview search API has no "has description"
# predicate; replace when Purview adds native userDescription:* query syntax.
_MAX_PAGE_SIZE = 1000
_MAX_RAW_SCAN = 10_000


async def search_assets_filtered(
    catalog: CatalogRepositoryInterface,
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
