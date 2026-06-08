import logging
import sys

import structlog
import uvicorn

from purview_mcp.infrastructure.auth.inbound_auth import EntraIDAuthMiddleware
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.presentation.container import build_container
from purview_mcp.presentation.mcp.server import create_server


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stderr, level=getattr(logging, level.upper(), logging.INFO))


def run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    _configure_logging(settings.log_level)

    log = structlog.get_logger("purview_mcp")
    log.info(
        "purview_mcp.starting",
        account=settings.purview_account_name,
        endpoint=settings.purview_endpoint,
    )

    container = build_container(settings)
    mcp = create_server(container)

    asgi_app = mcp.streamable_http_app()

    if settings.entra_audience and settings.azure_tenant_id:
        log.info("purview_mcp.auth.enabled", audience=settings.entra_audience)
        serve: object = EntraIDAuthMiddleware(
            asgi_app, settings.azure_tenant_id, settings.entra_audience
        )
    else:
        log.warning(
            "purview_mcp.auth.disabled",
            reason="ENTRA_AUDIENCE or AZURE_TENANT_ID not set — inbound requests are unauthenticated",
        )
        serve = asgi_app

    log.info("purview_mcp.listening", host=settings.host, port=settings.port)
    uvicorn.run(serve, host=settings.host, port=settings.port)  # type: ignore[arg-type]


if __name__ == "__main__":
    run()
