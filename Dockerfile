FROM python:3.12-slim AS builder

RUN pip install uv --quiet

WORKDIR /app

COPY pyproject.toml README.md uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

EXPOSE 8000

USER nobody

LABEL org.opencontainers.image.title="Purview MCP Server" \
      org.opencontainers.image.description="MCP server for Microsoft Purview Unified Catalog" \
      org.opencontainers.image.source="https://github.com/scardoso-lu/purview-mcp-server"

CMD ["python", "-m", "purview_mcp"]
