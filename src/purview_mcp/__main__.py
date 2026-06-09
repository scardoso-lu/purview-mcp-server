import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from starlette.applications import Starlette

from purview_mcp.infrastructure.auth.inbound_auth import EntraIDAuthMiddleware
from purview_mcp.infrastructure.config.settings import Settings
from purview_mcp.infrastructure.telemetry import configure_telemetry
from purview_mcp.presentation.container import build_container
from purview_mcp.presentation.mcp.server import create_server
from purview_mcp.presentation.middleware.rate_limit import RateLimitMiddleware


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        # add_logger_name requires a stdlib logger; PrintLoggerFactory crashes here.
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(stream=sys.stderr, level=getattr(logging, level.upper(), logging.INFO))


def run() -> None:
    settings = Settings()  # type: ignore[call-arg]
    _configure_logging(settings.log_level)
    tracer_provider = configure_telemetry(settings)

    log = structlog.get_logger("purview_mcp")
    log.info(
        "purview_mcp.starting",
        account=settings.purview_account_name,
        endpoint=settings.purview_endpoint,
    )

    container = build_container(settings)
    mcp = create_server(container)

    asgi_app = mcp.streamable_http_app()

    # Compose the FastMCP session-manager lifespan with client cleanup so
    # HTTP connections and the Azure credential are released on shutdown.
    inner_lifespan = asgi_app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with inner_lifespan(app):
            try:
                yield
            finally:
                await container.aclose()
                if tracer_provider is not None:
                    tracer_provider.shutdown()
                log.info("purview_mcp.shutdown.clients_closed")

    asgi_app.router.lifespan_context = lifespan

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

    if settings.rate_limit_per_minute > 0:
        log.info("purview_mcp.rate_limit.enabled", limit_per_minute=settings.rate_limit_per_minute)
        serve = RateLimitMiddleware(serve, settings.rate_limit_per_minute)
    else:
        log.warning("purview_mcp.rate_limit.disabled", reason="RATE_LIMIT_PER_MINUTE is 0")

    log.info("purview_mcp.listening", host=settings.host, port=settings.port)
    uvicorn.run(serve, host=settings.host, port=settings.port)  # type: ignore[arg-type]


if __name__ == "__main__":
    run()
