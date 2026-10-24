# Shortcuts for the commands CI runs. `make help` lists them. Every target is a thin wrapper:
# the real commands stay visible here, so nothing is hidden from a reader.
.DEFAULT_GOAL := help
.PHONY: help install db up down lint format typecheck test api-drift web-check check api-client context

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install Python and frontend packages exactly as the lockfiles say
	uv sync --locked
	cd frontend && npm ci

db: ## Start only Postgres + pgvector in Docker (what the tests need)
	docker compose up -d --wait db

up: ## Build and run the whole app at http://127.0.0.1:8000
	docker compose up --build

down: ## Stop the containers (the database volume is kept)
	docker compose down

lint: ## ruff lint + format check
	uv run ruff check
	uv run ruff format --check

format: ## Apply ruff formatting and safe lint fixes
	uv run ruff format
	uv run ruff check --fix

typecheck: ## mypy strict on src, tests and tools
	uv run mypy

test: ## pytest with coverage (needs Postgres on 127.0.0.1:5433)
	uv run pytest --cov --cov-report=term-missing:skip-covered

api-drift: ## Fail if frontend/openapi.json is out of date
	uv run python tools/export_openapi.py
	git diff --exit-code frontend/openapi.json

web-check: ## Frontend: Biome, TypeScript, production build
	cd frontend && npx biome ci . && npm run typecheck && npm run build

check: lint typecheck test api-drift web-check ## Every check CI runs (browser tests run in CI)

api-client: ## After an API change: export the schema and regenerate the TypeScript client
	uv run python tools/export_openapi.py
	cd frontend && npm run generate

context: ## Rebuild claude_context.md (the whole project in one file, for teaching)
	uv run python tools/make_context.py
