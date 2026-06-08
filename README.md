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
Claude / Copilot / Codex
         │
      MCP Client (stdio)
         │
  Purview MCP Server (Python / Onion Architecture)
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

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PURVIEW_ACCOUNT_NAME` | **Yes** | Your Purview account name (without `.purview.azure.com`) |
| `AZURE_TENANT_ID` | No | Azure tenant ID (for Service Principal auth) |
| `AZURE_CLIENT_ID` | No | App registration client ID |
| `AZURE_CLIENT_SECRET` | No | App registration client secret |
| `LOG_LEVEL` | No | Logging level: `DEBUG`, `INFO`, `WARNING` (default: `INFO`) |
| `RATE_LIMIT_PER_MINUTE` | No | API rate limit (default: `60`) |
| `OTEL_ENABLED` | No | Enable OpenTelemetry tracing (`true`/`false`, default: `false`) |

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

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_assets` | Search catalog assets by keyword |
| `get_asset_details` | Full metadata for an asset by GUID |
| `get_asset_lineage` | Upstream and downstream lineage graph |
| `get_asset_owner` | Business and technical owners |
| `search_glossary_terms` | Search business glossary definitions |
| `search_data_products` | Search Unified Catalog data products |
| `find_authoritative_source` | Identify the most trusted dataset for a concept |
| `get_data_quality` | Data quality metrics for an asset |

---

## Claude Desktop Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "purview": {
      "command": "python",
      "args": ["-m", "purview_mcp"],
      "cwd": "/absolute/path/to/purview-mcp-server",
      "env": {
        "PURVIEW_ACCOUNT_NAME": "your-account-name"
      }
    }
  }
}
```

See `claude-desktop-config.example.json` for a complete example.

---

## GitHub Copilot / VS Code Configuration

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "purview": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "purview_mcp"],
      "env": {
        "PURVIEW_ACCOUNT_NAME": "your-account-name"
      }
    }
  }
}
```

---

## Docker

### Build

```bash
docker build -t purview-mcp-server .
```

### Run

```bash
docker run --env-file .env purview-mcp-server
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
