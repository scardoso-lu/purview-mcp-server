import asyncio
import json
from typing import Any

import structlog

from purview_mcp.presentation.container import Container

logger = structlog.get_logger(__name__)

LIVENESS_PATH = "/healthz"
READINESS_PATH = "/readyz"


class HealthCheckEndpoints:
    """Outermost ASGI wrapper serving Kubernetes / Azure Container Apps probes.

    /healthz (liveness): 200 whenever the process is serving requests.
    /readyz (readiness): 200 when a Purview access token can be acquired,
    503 otherwise. The credential caches tokens, so probes are cheap after
    the first acquisition.

    Must sit outside auth and rate limiting so probes need no Bearer token
    and are never throttled.
    """

    def __init__(self, app: Any, container: Container, readiness_timeout: float = 5.0) -> None:
        self._app = app
        self._container = container
        self._readiness_timeout = readiness_timeout

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("method") not in ("GET", "HEAD"):
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == LIVENESS_PATH:
            await _send_json(send, 200, {"status": "ok"})
            return
        if path == READINESS_PATH:
            try:
                await asyncio.wait_for(
                    self._container.credential.get_token(), self._readiness_timeout
                )
            except Exception as exc:
                logger.warning("health.readiness_failed", error=type(exc).__name__)
                await _send_json(send, 503, {"status": "unready", "reason": type(exc).__name__})
                return
            await _send_json(send, 200, {"status": "ready"})
            return

        await self._app(scope, receive, send)


async def _send_json(send: Any, status: int, payload: dict[str, str]) -> None:
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})
