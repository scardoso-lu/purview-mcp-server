import asyncio
import uuid
from typing import Any

import httpx
import structlog
from opentelemetry import trace

from purview_mcp.domain.exceptions import (
    AssetNotFoundError,
    PurviewAPIError,
    RateLimitError,
)
from purview_mcp.infrastructure.auth.azure_credential import PurviewCredentialProvider

logger = structlog.get_logger(__name__)
_tracer = trace.get_tracer("purview_mcp.client")

_RETRY_DELAYS = [2.0, 4.0, 8.0]
_MAX_ATTEMPTS = len(_RETRY_DELAYS) + 1


class BaseClient:
    """Async HTTP client with auth injection, retry on 429/5xx, and structured audit logging."""

    def __init__(
        self,
        base_url: str,
        credential: PurviewCredentialProvider,
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._credential = credential
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_headers(self) -> dict[str, str]:
        token = await self._credential.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        return await self._request("POST", path, json=body)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}"
        correlation_id = str(uuid.uuid4())
        log = logger.bind(method=method, url=url, correlation_id=correlation_id)
        headers = await self._get_headers()

        with _tracer.start_as_current_span(
            f"purview.{method}",
            attributes={"http.method": method, "url.full": url},
        ) as span:
            return await self._request_with_retries(method, path, url, headers, log, span, **kwargs)

    async def _request_with_retries(
        self,
        method: str,
        path: str,
        url: str,
        headers: dict[str, str],
        log: Any,
        span: trace.Span,
        **kwargs: Any,
    ) -> Any:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            if attempt > 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt - 2])
            try:
                response = await self._client.request(method, url, headers=headers, **kwargs)
                log.debug("purview.api.response", status=response.status_code, attempt=attempt)
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("retry.attempts", attempt)

                if response.status_code == 429:
                    if attempt < _MAX_ATTEMPTS:
                        next_delay = _RETRY_DELAYS[attempt - 1]
                        log.warning("purview.api.rate_limited", retry_in=next_delay)
                        continue
                    raise RateLimitError()

                if response.status_code == 404:
                    raise AssetNotFoundError(path)

                if response.status_code >= 500:
                    if attempt < _MAX_ATTEMPTS:
                        next_delay = _RETRY_DELAYS[attempt - 1]
                        log.warning(
                            "purview.api.server_error",
                            status=response.status_code,
                            retry_in=next_delay,
                        )
                        continue
                    raise PurviewAPIError(
                        f"Purview API error {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                    )

                if response.is_error:
                    raise PurviewAPIError(
                        f"Purview API error {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                    )

                return response.json()

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                log.error("purview.api.request_failed", error=str(exc), attempt=attempt)
                if attempt >= _MAX_ATTEMPTS:
                    raise PurviewAPIError(str(exc)) from exc
                # network error on a non-final attempt — sleep and retry
                continue
