from azure.identity.aio import DefaultAzureCredential

PURVIEW_SCOPE = "https://purview.azure.net/.default"


class PurviewCredentialProvider:
    """Acquires Entra ID tokens for the Purview API.

    Uses the async DefaultAzureCredential from azure-identity, which handles
    token caching and proactive refresh internally via MSAL. Supports Managed
    Identity (Azure Container Apps), Service Principal (env vars), and Azure
    CLI (local development).
    """

    def __init__(self) -> None:
        self._credential = DefaultAzureCredential()

    async def get_token(self) -> str:
        token = await self._credential.get_token(PURVIEW_SCOPE)
        return token.token

    async def aclose(self) -> None:
        await self._credential.close()
