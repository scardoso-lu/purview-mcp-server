from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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
from purview_mcp.application.use_cases.search_undocumented_assets import (
    SearchUndocumentedAssetsUseCase,
)
from purview_mcp.domain.exceptions import ConfigurationError
from purview_mcp.domain.ports.catalog_port import ICatalogRepository
from purview_mcp.domain.ports.governance_port import IGovernanceRepository
from purview_mcp.domain.ports.lineage_port import ILineageRepository
from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider
from purview_mcp.infrastructure.clients.datamap_client import DataMapClient
from purview_mcp.infrastructure.clients.unified_catalog_client import UnifiedCatalogClient
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.infrastructure.db.engine import create_engine, create_sessionmaker
from purview_mcp.infrastructure.db.migrations import run_migrations
from purview_mcp.infrastructure.etl.extract import Extractor
from purview_mcp.infrastructure.etl.load import Loader
from purview_mcp.infrastructure.etl.scheduler import EtlScheduler
from purview_mcp.infrastructure.repositories.pg_catalog_repository import PgCatalogRepository
from purview_mcp.infrastructure.repositories.pg_governance_repository import PgGovernanceRepository
from purview_mcp.infrastructure.repositories.pg_lineage_repository import PgLineageRepository
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
    search_undocumented_assets: SearchUndocumentedAssetsUseCase
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
    db_engine: AsyncEngine | None = None
    db_sessionmaker: async_sessionmaker[AsyncSession] | None = None
    scheduler: EtlScheduler | None = None

    async def startup(self) -> None:
        """Async setup that must run inside the server event loop."""
        if self.db_engine is not None:
            await run_migrations(self.db_engine)
        if self.scheduler is not None:
            self.scheduler.start()

    async def aclose(self) -> None:
        """Release the ETL task, HTTP connections, credential, and DB engine."""
        if self.scheduler is not None:
            await self.scheduler.stop()
        await self.datamap_client.aclose()
        await self.unified_catalog_client.aclose()
        await self.credential.aclose()
        if self.db_engine is not None:
            await self.db_engine.dispose()


def build_container(settings: Settings) -> Container:
    credential = PurviewCredentialProvider()
    datamap = DataMapClient(settings.purview_endpoint, credential, settings.request_timeout_seconds)
    unified = UnifiedCatalogClient(
        settings.purview_endpoint, credential, settings.request_timeout_seconds
    )

    engine: AsyncEngine | None = None
    sessionmaker: async_sessionmaker[AsyncSession] | None = None
    scheduler: EtlScheduler | None = None

    catalog_repo: ICatalogRepository
    lineage_repo: ILineageRepository
    governance_repo: IGovernanceRepository

    backend = settings.serving_backend
    if backend == "postgres" and not settings.database_url:
        # Fail fast: postgres serving was requested but no database is configured.
        # The caller (__main__) turns this into a clean exit(1). To run without a
        # database, explicitly set SERVING_BACKEND=purview.
        raise ConfigurationError(
            "SERVING_BACKEND=postgres requires DATABASE_URL "
            "(e.g. postgresql+asyncpg://user:pass@host:5432/purview). "
            "Set DATABASE_URL, or set SERVING_BACKEND=purview to serve live "
            "from the Purview API without a database."
        )

    if backend == "postgres":
        assert settings.database_url is not None
        engine = create_engine(settings.database_url)
        sessionmaker = create_sessionmaker(engine)
        catalog_repo = PgCatalogRepository(sessionmaker)
        lineage_repo = PgLineageRepository(sessionmaker)
        governance_repo = PgGovernanceRepository(sessionmaker)

        if settings.etl_enabled:
            loader = Loader(sessionmaker, settings.etl_batch_size)
            extractor = Extractor(datamap, unified, settings.etl_lineage_depth)
            scheduler = EtlScheduler(
                loader,
                extractor,
                interval_seconds=settings.etl_interval_seconds,
                full_reconcile_every_n_runs=settings.etl_full_reconcile_every_n_runs,
                concurrency=settings.etl_concurrency,
            )
    else:
        catalog_repo = PurviewCatalogRepository(datamap)
        lineage_repo = PurviewLineageRepository(datamap)
        governance_repo = PurviewGovernanceRepository(datamap, unified)

    return Container(
        search_assets=SearchAssetsUseCase(catalog_repo),
        search_undocumented_assets=SearchUndocumentedAssetsUseCase(catalog_repo),
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
        db_engine=engine,
        db_sessionmaker=sessionmaker,
        scheduler=scheduler,
    )
