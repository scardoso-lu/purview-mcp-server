from __future__ import annotations

from typing import Any

import structlog


class Logger:
    """App-wide structured-log facade — one instance per service, injected via DI.

    Wraps structlog so business code never calls structlog directly.
    """

    def __init__(self, service: str) -> None:
        self._inner = structlog.get_logger().bind(service=service)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._inner.debug(event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._inner.info(event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._inner.warning(event, **kwargs)

    def error(
        self, event: str, exc_info: BaseException | bool | None = None, **kwargs: Any
    ) -> None:
        self._inner.error(event, exc_info=exc_info, **kwargs)

    def critical(
        self, event: str, exc_info: BaseException | bool | None = None, **kwargs: Any
    ) -> None:
        self._inner.critical(event, exc_info=exc_info, **kwargs)

    def bind(self, **kwargs: Any) -> Logger:
        new = Logger.__new__(Logger)
        new._inner = self._inner.bind(**kwargs)
        return new
