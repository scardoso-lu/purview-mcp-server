import logging
import sys

import structlog

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
    settings = Settings()  # type: ignore[call-arg]  # reads from env via pydantic-settings
    _configure_logging(settings.log_level)

    log = structlog.get_logger("purview_mcp")
    log.info(
        "purview_mcp.starting",
        account=settings.purview_account_name,
        endpoint=settings.purview_endpoint,
    )

    container = build_container(settings)
    mcp = create_server(container)
    log.info("purview_mcp.listening", host=settings.host, port=settings.port)
    mcp.run(transport="streamable-http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
