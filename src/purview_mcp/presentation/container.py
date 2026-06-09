from dataclasses import dataclass

from purview_mcp.application.use_cases.find_authoritative_source import (
    FindAuthoritativeSourceUseCase,
)
from purview_mcp.application.use_cases.get_asset_details import GetAssetDetailsUseCase
from purview_mcp.application.use_cases.get_asset_lineage import GetAssetLineageUseCase
from purview_mcp.application.use_cases.get_asset_owner import GetAssetOwnerUseCase
from purview_mcp.application.use_cases.get_data_quality import GetDataQualityUseCase
from purview_mcp.application.use_cases.search_assets import SearchAssetsUseCase
from purview_mcp.application.use_cases.search_data_products import SearchDataProductsUseCase
from purview_mcp.application.use_cases.search_glossary_terms import SearchGlossaryTermsUseCase
from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.infrastructure.repositories.purview_catalog_repository import (
    PurviewCatalogRepository,
)
from purview_mcp.infrastructure.repositories.purview_governance_repository import (
    PurviewGovernanceRepository,
)
from purview_mcp.infrastructure.repositories.purview_lineage_repository import (
    PurviewLineageRepository,
)


@dataclass
class Container:
    search_assets: SearchAssetsUseCase
    get_asset_details: GetAssetDetailsUseCase
    get_asset_lineage: GetAssetLineageUseCase
    get_asset_owner: GetAssetOwnerUseCase
    search_glossary_terms: SearchGlossaryTermsUseCase
    search_data_products: SearchDataProductsUseCase
    find_authoritative_source: FindAuthoritativeSourceUseCase
    get_data_quality: GetDataQualityUseCase
    datamap_client: DataMapClient
    unified_catalog_client: UnifiedCatalogClient
    credential: PurviewCredentialProvider

    async def aclose(self) -> None:
        """Release HTTP connections and the Azure credential on shutdown."""
        await self.datamap_client.aclose()
        await self.unified_catalog_client.aclose()
        await self.credential.aclose()


def build_container(settings: Settings) -> Container:
    credential = PurviewCredentialProvider()
    datamap = DataMapClient(settings.purview_endpoint, credential, settings.request_timeout_seconds)
    unified = UnifiedCatalogClient(
        settings.purview_endpoint, credential, settings.request_timeout_seconds
    )

    catalog_repo = PurviewCatalogRepository(datamap)
    lineage_repo = PurviewLineageRepository(datamap)
    governance_repo = PurviewGovernanceRepository(datamap, unified)

    return Container(
        search_assets=SearchAssetsUseCase(catalog_repo),
        get_asset_details=GetAssetDetailsUseCase(catalog_repo),
        get_asset_lineage=GetAssetLineageUseCase(lineage_repo),
        get_asset_owner=GetAssetOwnerUseCase(catalog_repo),
        search_glossary_terms=SearchGlossaryTermsUseCase(governance_repo),
        search_data_products=SearchDataProductsUseCase(governance_repo),
        find_authoritative_source=FindAuthoritativeSourceUseCase(catalog_repo),
        get_data_quality=GetDataQualityUseCase(catalog_repo),
        datamap_client=datamap,
        unified_catalog_client=unified,
        credential=credential,
    )
