import time
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient
from pytest_mock import MockerFixture

from purview_mcp.infrastructure.auth.inbound_auth import EntraIDAuthMiddleware

_TENANT_ID = "11111111-1111-1111-1111-111111111111"
_AUDIENCE = "api://test-server-app"
_ISSUER = f"https://login.microsoftonline.com/{_TENANT_ID}/v2.0"
_KID = "test-key-1"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks() -> dict[str, Any]:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(_private_key.public_key(), as_dict=True)
    jwk.update({"kid": _KID, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


def _make_token(
    *,
    aud: str = _AUDIENCE,
    iss: str = _ISSUER,
    exp_offset: int = 3600,
    key: rsa.RSAPrivateKey = _private_key,
) -> str:
    now = int(time.time())
    claims = {"aud": aud, "iss": iss, "iat": now, "exp": now + exp_offset, "sub": "user-1"}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": _KID})


async def _inner_app(scope: Any, receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok", "more_body": False})


@pytest.fixture
def middleware(mocker: MockerFixture) -> EntraIDAuthMiddleware:
    mocker.patch.object(PyJWKClient, "fetch_data", return_value=_jwks())
    return EntraIDAuthMiddleware(_inner_app, _TENANT_ID, _AUDIENCE)


def _client(middleware: EntraIDAuthMiddleware) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=middleware)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_valid_token_reaches_app(middleware: EntraIDAuthMiddleware) -> None:
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {_make_token()}"})
    assert resp.status_code == 200
    assert resp.text == "ok"


@pytest.mark.asyncio
async def test_missing_header_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    async with _client(middleware) as client:
        resp = await client.get("/")
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_token"
    assert resp.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_non_bearer_header_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_token"


@pytest.mark.asyncio
async def test_expired_token_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    token = _make_token(exp_offset=-3600)
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "token_expired"


@pytest.mark.asyncio
async def test_wrong_audience_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    token = _make_token(aud="api://someone-else")
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_wrong_issuer_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    token = _make_token(iss="https://evil.example.com/v2.0")
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_wrong_signing_key_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    token = _make_token(key=_other_key)
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_garbage_token_returns_401(middleware: EntraIDAuthMiddleware) -> None:
    async with _client(middleware) as client:
        resp = await client.get("/", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"


@pytest.mark.asyncio
async def test_jwks_fetched_once_across_requests(mocker: MockerFixture) -> None:
    fetch = mocker.patch.object(PyJWKClient, "fetch_data", return_value=_jwks())
    middleware = EntraIDAuthMiddleware(_inner_app, _TENANT_ID, _AUDIENCE)
    async with _client(middleware) as client:
        for _ in range(2):
            resp = await client.get("/", headers={"Authorization": f"Bearer {_make_token()}"})
            assert resp.status_code == 200
    assert fetch.call_count == 1


@pytest.mark.asyncio
async def test_non_http_scope_passes_through(
    middleware: EntraIDAuthMiddleware, mocker: MockerFixture
) -> None:
    inner = mocker.AsyncMock()
    middleware._app = inner
    scope = {"type": "lifespan"}
    receive = mocker.AsyncMock()
    send = mocker.AsyncMock()
    await middleware(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)
