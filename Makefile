SHELL := /bin/sh

.PHONY: help up down logs ps sh lock sync test test-file test-coverage lint lint-fix typecheck fmt check

help:
	@echo "payments-core commands:"
	@echo "  make up          Start API (foreground)"
	@echo "  make down        Stop services"
	@echo "  make logs        Tail logs"
	@echo "  make ps          Show running containers"
	@echo "  make sh          Shell inside api container"
	@echo "  make lock        Generate/update uv.lock"
	@echo "  make sync        Install deps from lock (frozen)"
	@echo "  make test        Run all tests"
	@echo "  make test-file   Run specific test file (FILE=path/to/test.py)"
	@echo "  make test-coverage  Run tests with coverage report"
	@echo "  make lint        Ruff check"
	@echo "  make lint-fix    Ruff check and fix"
	@echo "  make fmt         Ruff format"
	@echo "  make typecheck   Mypy strict typecheck"
	@echo "  make check       Lint + typecheck + test"


up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

sh:
	docker compose run --rm api sh

lock:
	docker compose run --rm api uv lock

sync:
	docker compose run --rm api uv sync --frozen --all-extras

test:
	docker compose run --rm api uv run pytest

test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required. Usage: make test-file FILE=path/to/test.py"; \
		exit 1; \
	fi
	docker compose run --rm api uv run pytest $(FILE) -v

test-coverage:
	docker compose run --rm api uv run pytest --cov=src/payments_core --cov-report=term-missing

lint:
	docker compose run --rm api uv run ruff check .

lint-fix:
	docker compose run --rm api uv run ruff check --fix .

fmt:
	docker compose run --rm api uv run ruff format .

typecheck:
	docker compose run --rm api uv run mypy src

check: lint typecheck test
