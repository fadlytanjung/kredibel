# Kredibel Makefile — unified developer workflow
# Run `make help` to inspect available commands.

SHELL := /usr/bin/env bash
PROJECT_ID ?= cloud-hack2skill
REGION ?= asia-southeast1
SCENARIO ?= S1
SEED ?= 1
ENV ?= local

.PHONY: help setup dev check test synth gen-api record evals deploy tokens tokens-check mocks mock-shots dev-agents migrate migrate-dry migrate-status docker-up docker-down schema-snapshot

help: ## Show this help message
	@echo "Kredibel — Developer Commands"
	@echo "Usage: make <target>"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install all backend, frontend, and synthetic dependencies
	@echo "==> Setting up backend (uv)..."
	@if [ -f backend/pyproject.toml ]; then cd backend && uv sync; fi
	@echo "==> Setting up frontend (npm)..."
	@if [ -f frontend/package.json ]; then cd frontend && npm install; fi
	@echo "==> Setting up synthetic data tools..."
	@if [ -f tools/synthetic/pyproject.toml ]; then cd tools/synthetic && uv sync; fi
	@echo "==> Setup complete."

dev: ## Run local dev servers (FastAPI on :8000 + worker inline, Vite on :5173)
	@echo "Starting Kredibel in local dev mode..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi
	@make docker-up
	@echo "Starting backend and frontend..."
	@concurrently "make dev-backend" "make dev-frontend" 2>/dev/null || ( \
		echo "Run backend: (cd backend && uv run uvicorn app.main:app --reload --port 8000)"; \
		echo "Run frontend: (cd frontend && npm run dev)" \
	)

dev-backend: ## Run local backend with reload
	cd backend && APP_ROLE=all TASK_QUEUE_MODE=inline uv run uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run local frontend Vite dev server
	cd frontend && npm run dev

docker-up: ## Start local Firestore emulator in Docker
	docker compose up -d firestore

docker-down: ## Stop local Firestore emulator
	docker compose down

check: ## Run all quality gates (lint, types, layers, repo checks, tests)
	@echo "==> Running quality gates..."
	@echo "1. Checking Python linting (ruff)..."
	@if [ -f backend/pyproject.toml ]; then cd backend && uv run ruff check .; fi
	@echo "2. Checking Python types (pyright)..."
	@if [ -f backend/pyproject.toml ]; then cd backend && uv run pyright; fi
	@echo "3. Checking architecture boundaries (.importlinter)..."
	@if [ -f backend/.importlinter ]; then cd backend && uv run lint-imports; fi
	@echo "4. Running custom repo checks..."
	@if [ -f tools/checks/no_long_prompts.py ]; then python3 tools/checks/no_long_prompts.py; fi
	@if [ -f tools/checks/scan_secrets.py ]; then python3 tools/checks/scan_secrets.py; fi
	@if [ -f tools/checks/schema_drift.py ]; then python3 tools/checks/schema_drift.py; fi
	@if [ -f tools/checks/no_raw_styles.py ]; then python3 tools/checks/no_raw_styles.py; fi
	@if [ -f tools/design/build_tokens.py ]; then python3 tools/design/build_tokens.py --check; fi
	@echo "5. Running backend tests (pytest)..."
	@if [ -f backend/pyproject.toml ]; then cd backend && uv run pytest; fi
	@echo "6. Checking frontend linting and types..."
	@if [ -f frontend/package.json ]; then cd frontend && npm run lint && npm run check; fi
	@echo "7. Running frontend tests (vitest)..."
	@if [ -f frontend/package.json ]; then cd frontend && npm test -- --run; fi
	@echo "==> All gates passed."

test: ## Run unit and integration tests
	cd backend && uv run pytest

synth: ## Generate synthetic scenarios
	@echo "==> Generating synthetic test scenarios..."
	cd tools/synthetic && uv run python -m synthetic.cli generate

gen-api: ## Regenerate frontend TypeScript types from OpenAPI spec
	@echo "==> Generating frontend API types from contracts/openapi.yaml..."
	./frontend/node_modules/.bin/openapi-typescript contracts/openapi.yaml -o frontend/src/shared/api/schema.d.ts

record: ## Record real extractor outputs for a scenario (e.g. make record SCENARIO=S2 SEED=1)
	@echo "==> Recording extractor output for scenario $(SCENARIO)..."
	cd backend && uv run python -m app.adapters.record --scenario=$(SCENARIO) --seed=$(SEED)

evals: ## Run model evaluations (DeepEval)
	@echo "==> Running model evals..."
	cd backend && uv run python -m evals.runner

deploy: ## Deploy to Cloud Run via Cloud Build
	@echo "==> Submitting Cloud Build for project $(PROJECT_ID)..."
	gcloud builds submit --config=cloudbuild.yaml --substitutions=_PROJECT_ID=$(PROJECT_ID)

tokens: ## Regenerate CSS from design tokens
	python3 tools/design/build_tokens.py

tokens-check: ## Check contrast and tokens
	python3 tools/design/build_tokens.py --check

mocks: ## Regenerate HTML mocks from tools/design/mocks/
	python3 tools/design/mocks/build_mocks.py

mock-shots: ## Take screenshots of HTML mocks for docs
	uv run --with playwright --with pillow python tools/design/shoot_mocks.py

dev-agents: ## Launch ADK developer UI for agent inspection
	cd backend && uv run adk web --port 8501

migrate-dry: ## Dry-run pending data migrations
	cd backend && uv run python -m migrations.runner --dry-run --env=$(ENV)

migrate: ## Execute pending data migrations
	cd backend && uv run python -m migrations.runner --env=$(ENV)

migrate-status: ## Check migration status
	cd backend && uv run python -m migrations.runner --status --env=$(ENV)

schema-snapshot: ## Regenerate Firestore data schema snapshot
	python3 tools/checks/schema_drift.py --write
