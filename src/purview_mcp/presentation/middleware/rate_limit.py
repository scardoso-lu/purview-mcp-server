import json
import time
from collections import deque
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_WINDOW_SECONDS = 60.0


class RateLimitMiddleware:
    """Pure ASGI middleware enforcing a per-client sliding-window rate limit.

    Requests are keyed by peer IP (``scope["client"]``). Behind a reverse proxy
    all traffic shares the proxy's address unless the ASGI server is configured
    to honor proxy headers (e.g. uvicorn ``--proxy-headers``).

    State is in-memory and per-process; horizontal replicas each apply the
    limit independently.

    Enable by setting RATE_LIMIT_PER_MINUTE > 0 (default 60). Set it to 0 to
    disable; __main__.py skips wrapping in that case.
    """

    def __init__(self, app: Any, limit_per_minute: int) -> None:
        self._app = app
        self._limit = limit_per_minute
        self._windows: dict[str, deque[float]] = {}

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.monotonic()

        window = self._windows.setdefault(key, deque())
        while window and now - window[0] >= _WINDOW_SECONDS:
            window.popleft()

        if len(window) >= self._limit:
            retry_after = int(_WINDOW_SECONDS - (now - window[0])) + 1
            logger.warning("rate_limit.rejected", client=key, retry_after=retry_after)
            await _send_429(send, retry_after)
            return

        window.append(now)
        # Prune idle keys so the map doesn't grow unboundedly with one-off clients.
        if len(self._windows) > 1024:
            for k in [k for k, w in self._windows.items() if not w]:
                del self._windows[k]

        await self._app(scope, receive, send)


async def _send_429(send: Any, retry_after: int) -> None:
    body = json.dumps(
        {
            "error": "rate_limited",
            "error_description": f"Rate limit exceeded; retry after {retry_after} seconds",
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(retry_after).encode()),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})
