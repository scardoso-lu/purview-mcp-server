from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    purview_account_name: str
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None
    # Inbound auth: Application ID URI of the server app registration, e.g. api://<client-id>
    entra_audience: str | None = None
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    rate_limit_per_minute: int = 60
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    request_timeout_seconds: int = 30

    # --- ETL / PostgreSQL-backed serving ---
    # Async SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host:5432/purview
    database_url: str | None = None
    # Which repository implementations the MCP tools read from:
    #   "postgres" -> serve from the ETL-populated database (default)
    #   "purview"  -> serve live from the Purview API (rollback lever / no-DB mode)
    serving_backend: str = "postgres"
    etl_enabled: bool = True
    etl_interval_seconds: int = 900
    # Every Nth scheduled run is a full reconcile (delete detection); others are incremental.
    etl_full_reconcile_every_n_runs: int = 24
    etl_concurrency: int = 6
    etl_batch_size: int = 500
    etl_lineage_depth: int = 3

    @property
    def purview_endpoint(self) -> str:
        return f"https://{self.purview_account_name}.purview.azure.com"
