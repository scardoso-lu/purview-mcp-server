import json
from typing import Any

import pytest
from pytest_mock import MockerFixture

from purview_mcp.presentation.middleware.rate_limit import RateLimitMiddleware


async def _inner_app(scope: Any, receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok", "more_body": False})


def _http_scope(client_ip: str = "10.0.0.1") -> dict[str, Any]:
    return {"type": "http", "client": (client_ip, 1234), "headers": []}


async def _call(
    middleware: RateLimitMiddleware, scope: dict[str, Any]
) -> tuple[int, bytes, dict[bytes, bytes]]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await middleware(scope, receive, send)
    status = messages[0]["status"]
    headers = dict(messages[0].get("headers", []))
    body = b"".join(m.get("body", b"") for m in messages[1:])
    return status, body, headers


@pytest.mark.asyncio
async def test_allows_requests_under_limit() -> None:
    middleware = RateLimitMiddleware(_inner_app, limit_per_minute=2)
    for _ in range(2):
        status, body, _ = await _call(middleware, _http_scope())
        assert status == 200
        assert body == b"ok"


@pytest.mark.asyncio
async def test_rejects_request_over_limit() -> None:
    middleware = RateLimitMiddleware(_inner_app, limit_per_minute=2)
    for _ in range(2):
        await _call(middleware, _http_scope())

    status, body, headers = await _call(middleware, _http_scope())
    assert status == 429
    assert json.loads(body)["error"] == "rate_limited"
    assert b"retry-after" in headers
    assert int(headers[b"retry-after"]) >= 1


@pytest.mark.asyncio
async def test_clients_tracked_independently() -> None:
    middleware = RateLimitMiddleware(_inner_app, limit_per_minute=1)
    status_a, _, _ = await _call(middleware, _http_scope("10.0.0.1"))
    status_b, _, _ = await _call(middleware, _http_scope("10.0.0.2"))
    assert status_a == 200
    assert status_b == 200

    status_a2, _, _ = await _call(middleware, _http_scope("10.0.0.1"))
    assert status_a2 == 429


@pytest.mark.asyncio
async def test_window_expires(mocker: MockerFixture) -> None:
    clock = mocker.patch(
        "purview_mcp.presentation.middleware.rate_limit.time.monotonic", return_value=1000.0
    )
    middleware = RateLimitMiddleware(_inner_app, limit_per_minute=1)

    status, _, _ = await _call(middleware, _http_scope())
    assert status == 200
    status, _, _ = await _call(middleware, _http_scope())
    assert status == 429

    clock.return_value = 1061.0
    status, _, _ = await _call(middleware, _http_scope())
    assert status == 200


@pytest.mark.asyncio
async def test_non_http_scope_passes_through(mocker: MockerFixture) -> None:
    inner = mocker.AsyncMock()
    middleware = RateLimitMiddleware(inner, limit_per_minute=1)
    scope = {"type": "lifespan"}
    receive = mocker.AsyncMock()
    send = mocker.AsyncMock()
    await middleware(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)
