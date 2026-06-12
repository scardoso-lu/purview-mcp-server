class PurviewError(Exception):
    """Base exception for all Purview MCP errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AssetNotFoundError(PurviewError):
    def __init__(self, asset_id: str) -> None:
        super().__init__(f"Asset not found: {asset_id}", status_code=404)
        self.asset_id = asset_id


class AuthenticationError(PurviewError):
    def __init__(self, detail: str = "Failed to authenticate with Microsoft Entra ID") -> None:
        super().__init__(detail, status_code=401)


class RateLimitError(PurviewError):
    def __init__(self) -> None:
        super().__init__("Purview API rate limit exceeded", status_code=429)


class PurviewAPIError(PurviewError):
    pass


class ConfigurationError(PurviewError):
    """Raised when the server is misconfigured and cannot start."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
