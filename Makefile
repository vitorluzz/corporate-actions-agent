# Asset Servicing Agent — one-command workflows.
# Backend uses uv. Frontend uses npm. Postgres via docker compose.

BACKEND := backend
# Prefer the docker compose v2 plugin; fall back to legacy docker-compose v1.
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")
COMPOSE := $(COMPOSE) -f infra/docker-compose.yml

.DEFAULT_GOAL := help

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install backend (uv) deps
	cd $(BACKEND) && uv sync --extra dev

.PHONY: db-up
db-up: ## Start Postgres
	$(COMPOSE) up -d postgres

.PHONY: db-down
db-down: ## Stop Postgres
	$(COMPOSE) down

.PHONY: run
run: ## Run the batch over documents/ -> outputs/ (offline stub if no API key)
	cd $(BACKEND) && uv run asset-agent run

.PHONY: replay
replay: ## Reproduce outputs from the response cache (no LLM calls)
	cd $(BACKEND) && uv run asset-agent run --replay

.PHONY: api
api: ## Start the FastAPI backend (review console API)
	cd $(BACKEND) && uv run uvicorn app.api.main:app --reload --port 8000

.PHONY: web
web: ## Start the React review console (Vite dev server)
	cd frontend && npm install && npm run dev

.PHONY: test
test: ## Run backend tests
	cd $(BACKEND) && uv run pytest -q

.PHONY: lint
lint: ## Lint backend
	cd $(BACKEND) && uv run ruff check app tests
