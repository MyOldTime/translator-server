FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    APP_HOST=0.0.0.0 \
    APP_PORT=8191

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md .python-version ./
COPY src ./src

RUN uv sync --frozen --no-dev

COPY models ./models

EXPOSE 8191

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "translator_server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8191"]
