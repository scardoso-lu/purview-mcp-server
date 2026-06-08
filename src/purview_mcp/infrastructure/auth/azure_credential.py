import time

import structlog
from azure.identity import DefaultAzureCredential

from purview_mcp.domain.exceptions import AuthenticationError

logger = structlog.get_logger(__name__)

PURVIEW_SCOPE = "https://purview.azure.net/.default"
_TOKEN_REFRESH_BUFFER_SECONDS = 300  # refresh 5 min before expiry


class PurviewCredentialProvider:
    """Wraps DefaultAzureCredential with token caching for Purview APIs.

    Supports: Service Principal (env vars), Managed Identity, az login.
    """

    def __init__(self) -> None:
        self._credential = DefaultAzureCredential()
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0

    async def get_token(self) -> str:
        if self._cached_token and time.time() < self._token_expires_at:
            return self._cached_token
        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        try:
            token = self._credential.get_token(PURVIEW_SCOPE)
            self._cached_token = token.token
            self._token_expires_at = token.expires_on - _TOKEN_REFRESH_BUFFER_SECONDS
            logger.debug("purview.token.refreshed")
            return token.token
        except Exception as exc:
            logger.error("purview.token.refresh_failed", error=str(exc))
            raise AuthenticationError(str(exc)) from exc
