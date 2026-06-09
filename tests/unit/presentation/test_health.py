import asyncio
import json
from typing import Any

import pytest
from pytest_mock import MockerFixture

from purview_mcp.presentation.middleware.health import HealthCheckEndpoints


async def _inner_app(scope: Any, receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"app", "more_body": False})


def _scope(path: str, method: str = "GET") -> dict[str, Any]:
    return {"type": "http", "method": method, "path": path, "headers": []}


async def _call(middleware: HealthCheckEndpoints, scope: dict[str, Any]) -> tuple[int, bytes]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await middleware(scope, receive, send)
    body = b"".join(m.get("body", b"") for m in messages[1:])
    return messages[0]["status"], body


def _middleware(mocker: MockerFixture, **kwargs: Any) -> tuple[HealthCheckEndpoints, Any]:
    container = mocker.MagicMock()
    container.credential.get_token = mocker.AsyncMock(return_value="tok")
    return HealthCheckEndpoints(_inner_app, container, **kwargs), container


@pytest.mark.asyncio
async def test_liveness_returns_ok(mocker: MockerFixture) -> None:
    middleware, container = _middleware(mocker)
    status, body = await _call(middleware, _scope("/healthz"))
    assert status == 200
    assert json.loads(body)["status"] == "ok"
    container.credential.get_token.assert_not_called()


@pytest.mark.asyncio
async def test_liveness_ok_even_when_credential_broken(mocker: MockerFixture) -> None:
    middleware, container = _middleware(mocker)
    container.credential.get_token.side_effect = RuntimeError("no credentials")
    status, _ = await _call(middleware, _scope("/healthz"))
    assert status == 200


@pytest.mark.asyncio
async def test_readiness_ready_when_token_acquired(mocker: MockerFixture) -> None:
    middleware, container = _middleware(mocker)
    status, body = await _call(middleware, _scope("/readyz"))
    assert status == 200
    assert json.loads(body)["status"] == "ready"
    container.credential.get_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_readiness_unready_when_token_fails(mocker: MockerFixture) -> None:
    middleware, container = _middleware(mocker)
    container.credential.get_token.side_effect = RuntimeError("no credentials")
    status, body = await _call(middleware, _scope("/readyz"))
    assert status == 503
    payload = json.loads(body)
    assert payload["status"] == "unready"
    assert payload["reason"] == "RuntimeError"


@pytest.mark.asyncio
async def test_readiness_unready_on_timeout(mocker: MockerFixture) -> None:
    middleware, container = _middleware(mocker, readiness_timeout=0.01)

    async def _hang() -> str:
        await asyncio.sleep(10)
        return "tok"

    container.credential.get_token = _hang
    status, body = await _call(middleware, _scope("/readyz"))
    assert status == 503
    assert json.loads(body)["reason"] == "TimeoutError"


@pytest.mark.asyncio
async def test_other_paths_pass_through(mocker: MockerFixture) -> None:
    middleware, _ = _middleware(mocker)
    status, body = await _call(middleware, _scope("/mcp"))
    assert status == 200
    assert body == b"app"


@pytest.mark.asyncio
async def test_post_to_health_path_passes_through(mocker: MockerFixture) -> None:
    middleware, _ = _middleware(mocker)
    status, body = await _call(middleware, _scope("/healthz", method="POST"))
    assert body == b"app"


@pytest.mark.asyncio
async def test_non_http_scope_passes_through(mocker: MockerFixture) -> None:
    inner = mocker.AsyncMock()
    middleware = HealthCheckEndpoints(inner, mocker.MagicMock())
    scope = {"type": "lifespan"}
    receive = mocker.AsyncMock()
    send = mocker.AsyncMock()
    await middleware(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)
