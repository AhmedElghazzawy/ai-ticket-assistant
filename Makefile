# Shortcuts for the commands CI runs. `make help` lists them. Every target is a thin wrapper:
# the real commands stay visible here, so nothing is hidden from a reader.
.DEFAULT_GOAL := help
# The package lives in src/helpdesk. It is installed in editable mode, but on macOS the .pth file
# that points there can get the "hidden" flag, which Python 3.12 skips; naming src/ is the fix.
export PYTHONPATH := src
.PHONY: help install db up down serve panel lint format typecheck test api-drift web-check check api-client context \
	data index eval-classifier eval-retrieval eval-pipeline eval-security

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

serve: ## API with auto-reload at http://127.0.0.1:8000 (frontend dev server: cd frontend && npm run dev)
	uv run uvicorn helpdesk.api.app:create_app --factory --reload

panel: ## The old Streamlit panel (dataset and eval results)
	uv run streamlit run src/helpdesk/panel.py

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

data: ## Check the dev tickets and print a summary (no AI calls)
	uv run python -m helpdesk.domain.tickets

index: ## Rebuild data/kb_index.json after a knowledge-base change (paid embedding calls)
	uv run python -m helpdesk.retrieval.search

# Evals call the paid model. SET=dev (default), test or phase8 (locked: measure only, never tune).
SET ?= dev
LEVEL ?= high
eval-classifier: ## Classifier eval: make eval-classifier LEVEL=high SET=dev
	uv run python -m helpdesk.evals.classifier $(LEVEL) $(SET)

eval-retrieval: ## Retrieval eval (hit@1, hit@3) on every set (embedding calls only)
	uv run python -m helpdesk.evals.retrieval

eval-pipeline: ## Whole pipeline: unsafe auto-sends, first help (make eval-pipeline SET=dev)
	uv run python -m helpdesk.evals.pipeline $(SET)

eval-security: ## Prompt-injection probes
	uv run python -m helpdesk.evals.security
