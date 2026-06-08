import httpx
import pytest
import respx
from pytest_mock import MockerFixture

from purview_mcp.domain.exceptions import AssetNotFoundError, PurviewAPIError, RateLimitError
from purview_mcp.infrastructure.clients.base_client import _MAX_ATTEMPTS, _RETRY_DELAYS, BaseClient


@pytest.fixture
def credential(mocker: MockerFixture) -> object:
    mock = mocker.AsyncMock()
    mock.get_token.return_value = "test-token"
    return mock


@pytest.fixture
def client(credential: object) -> BaseClient:
    return BaseClient(base_url="https://example.purview.azure.com", credential=credential)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_successful_get_returns_json(client: BaseClient) -> None:
    with respx.mock:
        respx.get("https://example.purview.azure.com/some/path").mock(
            return_value=httpx.Response(200, json={"key": "value"})
        )
        result = await client.get("/some/path")
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_404_raises_asset_not_found(client: BaseClient) -> None:
    with respx.mock:
        respx.get("https://example.purview.azure.com/entity/missing").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(AssetNotFoundError):
            await client.get("/entity/missing")


@pytest.mark.asyncio
async def test_500_retries_then_raises(client: BaseClient, mocker: MockerFixture) -> None:
    mocker.patch("asyncio.sleep")
    with respx.mock:
        route = respx.get("https://example.purview.azure.com/flaky").mock(
            return_value=httpx.Response(500, text="internal error")
        )
        with pytest.raises(PurviewAPIError):
            await client.get("/flaky")
        assert route.call_count == _MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_429_retries_then_raises_rate_limit(client: BaseClient, mocker: MockerFixture) -> None:
    mocker.patch("asyncio.sleep")
    with respx.mock:
        route = respx.get("https://example.purview.azure.com/rate-limited").mock(
            return_value=httpx.Response(429)
        )
        with pytest.raises(RateLimitError):
            await client.get("/rate-limited")
        assert route.call_count == _MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_transport_error_retries_then_raises(
    client: BaseClient, mocker: MockerFixture
) -> None:
    mocker.patch("asyncio.sleep")
    with respx.mock:
        route = respx.get("https://example.purview.azure.com/timeout").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        with pytest.raises(PurviewAPIError):
            await client.get("/timeout")
        assert route.call_count == _MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_transport_error_succeeds_on_retry(
    client: BaseClient, mocker: MockerFixture
) -> None:
    mocker.patch("asyncio.sleep")
    responses = [
        httpx.ConnectError("transient"),
        httpx.Response(200, json={"ok": True}),
    ]
    with respx.mock:
        respx.get("https://example.purview.azure.com/retry-ok").mock(side_effect=responses)
        result = await client.get("/retry-ok")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_retry_delays_match_config(client: BaseClient, mocker: MockerFixture) -> None:
    sleep_mock = mocker.patch("asyncio.sleep")
    with respx.mock:
        respx.get("https://example.purview.azure.com/slow").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(PurviewAPIError):
            await client.get("/slow")

    actual_delays = [call.args[0] for call in sleep_mock.call_args_list]
    assert actual_delays == _RETRY_DELAYS
