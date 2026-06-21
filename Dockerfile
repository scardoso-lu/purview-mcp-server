# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

# Install uv from the official image — no pip, no curl, no apt dependency
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy lockfile and manifest first — Docker layer cache only rebuilds
# the install layer when dependencies actually change
COPY pyproject.toml uv.lock ./


# ── production ────────────────────────────────────────────────────────────────
FROM base AS production

RUN uv sync --frozen --no-dev --no-install-project

COPY README.md LICENSE ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, sys, urllib.request; port = os.environ.get('PORT', '8000'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=4).status == 200 else 1)"

LABEL org.opencontainers.image.title="Purview MCP Server" \
      org.opencontainers.image.description="MCP server for Microsoft Purview Unified Catalog" \
      org.opencontainers.image.source="https://github.com/scardoso-lu/purview-mcp-server"

CMD ["uv", "run", "python", "-m", "purview_mcp"]


# ── test ──────────────────────────────────────────────────────────────────────
FROM base AS test

RUN uv sync --frozen --no-install-project

COPY README.md LICENSE ./
COPY src/ ./src/
COPY tests/ ./tests/
RUN uv sync --frozen

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

CMD ["uv", "run", "pytest", "tests/unit", "-v"]
