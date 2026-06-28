FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --frozen

FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app
COPY --from=builder /uv /uvx /bin/
COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/
COPY alembic.ini ./
COPY pyproject.toml ./

ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app && \
    chown -R app:app /app

USER app

EXPOSE 8000