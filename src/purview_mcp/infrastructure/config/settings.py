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
    log_level: str = "INFO"
    rate_limit_per_minute: int = 60
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    request_timeout_seconds: int = 30

    @property
    def purview_endpoint(self) -> str:
        return f"https://{self.purview_account_name}.purview.azure.com"
