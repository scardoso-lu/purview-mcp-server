from __future__ import annotations

import functools
from collections.abc import Callable, Coroutine
from typing import Any

from purview_mcp.domain.exceptions import (
    AssetNotFoundError,
    PurviewAPIError,
    PurviewError,
    RateLimitError,
)


def handle_tool_errors(
    fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    """Catch PurviewError at the MCP tool boundary and return a structured error dict."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return await fn(*args, **kwargs)
        except AssetNotFoundError as exc:
            return {"error": "not_found", "message": str(exc)}
        except RateLimitError as exc:
            return {"error": "rate_limited", "message": str(exc)}
        except PurviewAPIError as exc:
            return {"error": "api_error", "message": str(exc)}
        except PurviewError as exc:
            return {"error": "purview_error", "message": str(exc)}

    return wrapper
