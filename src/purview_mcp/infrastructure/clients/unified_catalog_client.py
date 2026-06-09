from typing import Any

from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider
from purview_mcp.infrastructure.clients.base_client import BaseClient

_DATA_PRODUCTS_API_VERSION = "2026-03-20-preview"
_CATALOG_BASE = "/datagovernance/catalog"


class UnifiedCatalogClient(BaseClient):
    """Client for the Purview Unified Catalog API (data products, domains)."""

    def __init__(
        self, endpoint: str, credential: PurviewCredentialProvider, timeout: int = 30
    ) -> None:
        super().__init__(endpoint, credential, timeout)

    async def query_data_products(
        self,
        keyword: str | None = None,
        limit: int = 10,
        domain_id: str | None = None,
        skip: int = 0,
    ) -> Any:
        body: dict[str, Any] = {"top": limit}
        if keyword:
            body["nameKeyword"] = keyword
        if domain_id:
            body["domainIds"] = [domain_id]
        if skip > 0:
            body["skip"] = skip
        return await self.post(
            f"{_CATALOG_BASE}/dataProducts/query?api-version={_DATA_PRODUCTS_API_VERSION}",
            body,
        )
