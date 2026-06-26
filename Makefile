HOST ?= 127.0.0.1
PORT ?= 8080
WORKERS_COUNT ?= 1

install:
	uv sync
	make migrate

migrate:
	uv run alembic upgrade head

lint:
	uv run black --check --diff .
	uv run ruff check .
	uv run mypy .

check_models:
	uv run alembic check

dev:
	uv run uvicorn src:app --host $(HOST) --port $(PORT) --reload

start_outbox_publish_worker:
	uv run -m src.workers.outbox_publisher.run_outbox_publish_worker

start_main_app:
	uv run uvicorn src:app --host $(HOST) --port $(PORT) --workers $(WORKERS_COUNT)

test:
	uv run pytest -v

test_unit:
	uv run pytest -v -m unit

test_integration:
	uv run pytest -v -m integration

test_cov:
	uv run pytest -v --cov=src --cov-report=term-missing --cov-report=html