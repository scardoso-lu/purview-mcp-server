import asyncio
import json
from typing import Any

import jwt
import structlog
from jwt import PyJWKClient

logger = structlog.get_logger(__name__)


class EntraIDAuthMiddleware:
    """Pure ASGI middleware that validates Entra ID Bearer tokens on every HTTP request.

    Fetches the tenant's JWKS once and caches signing keys. Each request validates
    the token's signature, issuer, and audience without a network call after the
    initial key fetch.

    Enable by setting ENTRA_AUDIENCE and AZURE_TENANT_ID in the environment.
    When ENTRA_AUDIENCE is unset, __main__.py skips wrapping so local dev works
    without credentials.
    """

    def __init__(self, app: Any, tenant_id: str, audience: str) -> None:
        self._app = app
        self._audience = audience
        self._issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self._jwks_client = PyJWKClient(jwks_uri, cache_keys=True)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        raw_auth = headers.get(b"authorization", b"").decode("latin-1")

        if not raw_auth.lower().startswith("bearer "):
            await _send_401(send, "missing_token", "Authorization header with Bearer token required")
            return

        token = raw_auth[7:]
        try:
            signing_key = await asyncio.to_thread(
                self._jwks_client.get_signing_key_from_jwt, token
            )
            jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
            )
        except jwt.ExpiredSignatureError:
            logger.warning("inbound_auth.token_expired")
            await _send_401(send, "token_expired", "Token has expired")
            return
        except (jwt.InvalidAudienceError, jwt.InvalidIssuerError) as exc:
            logger.warning("inbound_auth.token_claims_invalid", error=str(exc))
            await _send_401(send, "invalid_token", str(exc))
            return
        except Exception as exc:
            logger.warning("inbound_auth.token_validation_failed", error=type(exc).__name__)
            await _send_401(send, "invalid_token", "Token validation failed")
            return

        await self._app(scope, receive, send)


async def _send_401(send: Any, error: str, description: str) -> None:
    body = json.dumps({"error": error, "error_description": description}).encode()
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"www-authenticate", b"Bearer"),
            (b"content-length", str(len(body)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})
