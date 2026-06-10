# Microsoft Purview Unified Catalog MCP Server

An MCP (Model Context Protocol) server that exposes Microsoft Purview Unified Catalog metadata as AI-consumable tools for **Claude, GitHub Copilot, and OpenAI Codex**.

Built with Python following **Onion Architecture** and **Microsoft Entra ID** (Azure AD) authentication.

---

## What it does

Connects AI assistants to your Purview governance data so they can answer questions like:

- "What is the authoritative customer dataset?"
- "Who owns the Sales data product?"
- "Show lineage from SAP Customer Master to Power BI dashboards."
- "Which datasets contain GDPR-sensitive information?"
- "What glossary terms define 'Customer'?"

---

## Architecture

```
Claude / Copilot / Codex / Microsoft 365 Copilot
         │
      MCP Client (HTTP — streamable-http transport)
         │
  Purview MCP Server on Azure Container Apps (Python / Onion Architecture)
    ├── Presentation Layer  — MCP tools (FastMCP)
    ├── Application Layer   — Use cases
    ├── Domain Layer        — Models, ports
    └── Infrastructure      — Purview REST clients, Entra ID auth
         │
  Microsoft Purview APIs
    ├── DataMap API   https://{account}.purview.azure.com/datamap/api/
    └── Unified Catalog  https://{account}.purview.azure.com/datagovernance/catalog/
```

---

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Microsoft Purview account
- Azure CLI (`az login`) for local development

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/scardoso-lu/purview-mcp-server.git
cd purview-mcp-server
pip install uv
uv sync
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set PURVIEW_ACCOUNT_NAME
```

### 3. Authenticate (local development)

```bash
az login
```

### 4. Run

```bash
uv run python -m purview_mcp
```

The server starts on `http://0.0.0.0:8000`. The MCP endpoint is at `/mcp`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PURVIEW_ACCOUNT_NAME` | **Yes** | Your Purview account name (without `.purview.azure.com`) |
| `AZURE_TENANT_ID` | No | Azure tenant ID (for Service Principal auth) |
| `AZURE_CLIENT_ID` | No | App registration client ID |
| `AZURE_CLIENT_SECRET` | No | App registration client secret |
| `LOG_LEVEL` | No | Logging level: `DEBUG`, `INFO`, `WARNING` (default: `INFO`) |
| `HOST` | No | Bind address (default: `0.0.0.0`) |
| `PORT` | No | HTTP port (default: `8000`) |
| `RATE_LIMIT_PER_MINUTE` | No | Per-client (IP) request limit per minute; `0` disables (default: `60`) |
| `OTEL_ENABLED` | No | Enable OpenTelemetry tracing (`true`/`false`, default: `false`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTLP/HTTP collector endpoint (default: `http://localhost:4318`) |

---

## Authentication

Authentication uses `DefaultAzureCredential` from the Azure Identity SDK, which tries the following in order:

1. **Service Principal** — set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`
2. **Workload Identity** — AKS workload identity
3. **Managed Identity** — Azure VM / App Service / ACI
4. **Azure CLI** — local dev: `az login`
5. **Azure PowerShell** — local dev fallback

No secrets are stored in code.

---

## Health Checks

The server exposes unauthenticated probe endpoints (they bypass inbound auth and rate limiting):

| Endpoint | Purpose | Behavior |
|----------|---------|----------|
| `GET /healthz` | Liveness | `200` whenever the process is serving requests |
| `GET /readyz` | Readiness | `200` when a Purview access token can be acquired, `503` otherwise |

Use `/healthz` for container liveness probes and `/readyz` for readiness/startup probes
(Azure Container Apps health probes or Kubernetes `livenessProbe`/`readinessProbe`).
The Docker image also ships a `HEALTHCHECK` that polls `/healthz`.

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_assets` | Search catalog assets by keyword (returns only assets that have a description) |
| `search_undocumented_assets` | Search catalog assets that are missing a description |
| `get_asset_details` | Full metadata for an asset by GUID |
| `get_asset_lineage` | Upstream and downstream lineage graph |
| `get_asset_owner` | Business and technical owners |
| `search_glossary_terms` | Search business glossary definitions |
| `search_data_products` | Search Unified Catalog data products |
| `find_authoritative_source` | Identify the most trusted dataset for a concept |
| `get_data_quality` | Data quality metrics for an asset |

---

## Client Configuration

The server runs remotely on Azure Container Apps. All clients connect via HTTP to the `/mcp` endpoint.

---

## Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "purview": {
      "type": "http",
      "url": "https://<your-azure-container-url>/mcp"
    }
  }
}
```

See `claude-desktop-config.example.json` for a complete example.

---

## GitHub Copilot / VS Code Configuration

The `.vscode/mcp.json` in this repo is pre-configured. Replace the URL with your deployment:

```json
{
  "servers": {
    "purview": {
      "type": "http",
      "url": "https://<your-azure-container-url>/mcp"
    }
  }
}
```

---

## Microsoft 365 Copilot Configuration

The `appPackage/` directory contains everything needed to deploy this server as a Microsoft 365 Copilot declarative agent. Authentication uses **Microsoft Entra ID via OAuthPluginVault** — M365 Copilot acquires an Entra token on behalf of the signed-in user and sends it as a Bearer token; Azure Container Apps EasyAuth validates it before the request reaches the container.

### Step 1 — Configure Azure Container Apps EasyAuth

1. In the Azure portal, open your Container App → **Authentication** → **Add identity provider**
2. Select **Microsoft** and create a **new app registration** (the _server_ registration)
3. Note the **Application (client) ID** and set the **Application ID URI** (e.g. `api://<client-id>`)
4. Under **Exposed API**, add a scope: `access_as_user` — this is what M365 Copilot will request
5. Set **Unauthenticated requests** to **HTTP 401** so the container rejects token-less calls

EasyAuth will now validate every incoming Bearer token against this app registration before the request reaches the MCP server — no code changes needed in the server.

### Step 2 — Register the OAuth connection in Teams Developer Portal

1. Open [Teams Developer Portal](https://dev.teams.microsoft.com) → **Tools** → **OAuth client registration**
2. Create a new registration:
   - **Authorization endpoint**: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/authorize`
   - **Token endpoint**: `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`
   - **Scope**: `api://<server-app-client-id>/access_as_user`
   - **Client ID / Secret**: create a second _client_ app registration in Entra ID, grant it the `access_as_user` scope on the server app, and use its credentials here
3. Save — you will receive an **OAuth registration ID** (a UUID)

### Step 3 — Update ai-plugin.json and deploy

1. Edit `appPackage/ai-plugin.json`:
   - Replace `<entra-sso-registration-id>` with the OAuth registration ID from Step 2
   - Replace `<your-azure-container-url>` with your Container App URL
2. Edit `appPackage/manifest.json` and replace `<replace-with-a-new-guid>` with a new GUID
3. Add `color.png` (192×192 px) and `outline.png` (32×32 px, transparent) to `appPackage/`
4. In VS Code with the [Microsoft 365 Agents Toolkit](https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.ms-teams-vscode-extension), run **Provision** then **Deploy**
5. The agent becomes available in Microsoft 365 Copilot under your tenant

### Option B — Copilot Studio (no Teams Toolkit)

1. Complete Steps 1–2 above
2. Open [Copilot Studio](https://copilotstudio.microsoft.com) → **Actions** → **Add an action** → **Model Context Protocol**
3. Enter the server URL and configure the OAuth connection using the registration ID from Step 2

### Key files

| File | Purpose |
|------|---------|
| `appPackage/manifest.json` | Teams app manifest (v1.19) |
| `appPackage/declarativeAgent.json` | Agent name, instructions, and action bindings |
| `appPackage/ai-plugin.json` | MCP plugin manifest (schema v2.4, `RemoteMCPServer` + `OAuthPluginVault`) |

---

## Docker

### Build

```bash
docker build -t purview-mcp-server .
```

### Run

```bash
docker run --env-file .env -p 8000:8000 purview-mcp-server
```

### Docker Compose (local dev)

```bash
docker-compose up
```

---

## Development

### Run tests

```bash
uv run pytest tests/unit
```

### Lint and format

```bash
uv run ruff check src tests
uv run ruff format src tests
```

### Type check

```bash
uv run mypy src
```

### Integration tests (requires Purview)

```bash
PURVIEW_ACCOUNT_NAME=your-account uv run pytest tests/integration
```

---

## Example Prompts

```
"Which dataset is the authoritative source for customer information?"
"Show me all certified datasets in the Finance domain."
"Who owns the SAP Customer Master table?"
"What data flows downstream from the orders_fact table?"
"Find all datasets classified as containing personal data."
"What does 'Net Revenue' mean in our data glossary?"
```

---

## Required Purview Roles

The identity used by this server needs:

- **Data Reader** — for reading catalog assets, lineage, and glossary
- **Data Curator** — if you need to read collection-level metadata

Assign roles in the Purview Studio under **Data map → Collections → Role assignments**.

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
