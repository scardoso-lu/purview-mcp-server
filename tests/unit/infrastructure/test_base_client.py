import httpx
import pytest
import respx
from pytest_mock import MockerFixture

from purview_mcp.domain.exceptions import (
    AssetNotFoundError,
    PurviewAPIError,
    RateLimitError,
)
from purview_mcp.infrastructure.clients.base_client import BaseClient

_BASE_URL = "https://test.purview.azure.com"


class FakeCredential:
    async def get_token(self) -> str:
        return "test-token"


@pytest.fixture
def client(mocker: MockerFixture) -> BaseClient:
    mocker.patch("purview_mcp.infrastructure.clients.base_client.asyncio.sleep")
    return BaseClient(_BASE_URL, FakeCredential())  # type: ignore[arg-type]


@respx.mock
@pytest.mark.asyncio
async def test_injects_bearer_token(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/ok").mock(return_value=httpx.Response(200, json={"ok": True}))
    result = await client.get("/ok")

    assert result == {"ok": True}
    assert route.calls.last.request.headers["Authorization"] == "Bearer test-token"


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(
        side_effect=[httpx.Response(429), httpx.Response(200, json={"ok": True})]
    )
    result = await client.get("/x")

    assert result == {"ok": True}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_raises_rate_limit_after_exhausting_retries(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(return_value=httpx.Response(429))
    with pytest.raises(RateLimitError):
        await client.get("/x")
    assert route.call_count == 4


@respx.mock
@pytest.mark.asyncio
async def test_raises_api_error_after_exhausting_5xx_retries(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(PurviewAPIError) as exc_info:
        await client.get("/x")
    assert exc_info.value.status_code == 500
    assert route.call_count == 4


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_503_then_succeeds(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={})]
    )
    result = await client.get("/x")

    assert result == {}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_network_error_then_succeeds(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(
        side_effect=[httpx.ConnectError("refused"), httpx.Response(200, json={})]
    )
    result = await client.get("/x")

    assert result == {}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_raises_api_error_after_exhausting_network_retries(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(side_effect=httpx.ConnectTimeout("timeout"))
    with pytest.raises(PurviewAPIError):
        await client.get("/x")
    assert route.call_count == 4


@respx.mock
@pytest.mark.asyncio
async def test_no_retry_on_400(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/x").mock(return_value=httpx.Response(400, text="bad request"))
    with pytest.raises(PurviewAPIError) as exc_info:
        await client.get("/x")
    assert exc_info.value.status_code == 400
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_404_raises_asset_not_found(client: BaseClient) -> None:
    route = respx.get(f"{_BASE_URL}/missing").mock(return_value=httpx.Response(404))
    with pytest.raises(AssetNotFoundError):
        await client.get("/missing")
    assert route.call_count == 1
