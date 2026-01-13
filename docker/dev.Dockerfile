# syntax=docker/dockerfile:1
FROM python:3.14.2-slim AS base

# Copy uv binaries from Astral's distroless image (recommended by uv docs)
# (You can pin a uv version later; start unpinned for convenience.)
COPY --from=ghcr.io/astral-sh/uv:debian /usr/local/bin/uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:debian /usr/local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# Speed + reproducibility knobs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    PYTHONPATH=/app/src

# 1) Install dependencies in a cached layer (only lock + pyproject copied)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --all-extras

# 2) Copy the actual project and install it (editable is fine for dev)
COPY src ./src
COPY tests ./tests
RUN uv sync --frozen --all-extras

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uv", "run", "uvicorn", "payments_core.entrypoints.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
