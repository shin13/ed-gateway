FROM ghcr.io/astral-sh/uv:0.11.24 AS uv

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=uv /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
COPY chainlit.md ./
COPY .chainlit ./.chainlit
COPY public ./public
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "ed_gateway.api.app:app", "--host", "0.0.0.0", "--port", "8001"]
