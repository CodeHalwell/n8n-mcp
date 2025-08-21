FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl for healthcheck and uv
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY README.md ./
RUN uv sync --frozen --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "mcp_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
