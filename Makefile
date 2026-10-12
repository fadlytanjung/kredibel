# Kredibel Makefile — unified developer workflow
# Run `make help` to inspect available commands.

SHELL := /usr/bin/env bash
PROJECT_ID ?= cloud-hack2skill
REGION ?= asia-southeast1
SCENARIO ?= S1
SEED ?= 1
ENV ?= local

.PHONY: help setup dev check test synth gen-api record evals deploy deploy-hosting tokens tokens-check mocks mock-shots dev-agents migrate migrate-dry migrate-status docker-up docker-down schema-snapshot

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
	cd backend && APP_ROLE=all TASK_QUEUE_MODE=inline FIRESTORE_DATABASE=$${FIRESTORE_DATABASE:-kredibel} DATA_CLASS=$${DATA_CLASS:-real} uv run uvicorn app.main:app --reload --port 8000

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
	@if [ -f frontend/package.json ]; then cd frontend && npm run gen:api >/dev/null && npm run lint && npm run check; fi
	@echo "7. Running frontend tests (vitest)..."
	@if [ -f frontend/package.json ]; then cd frontend && npm test -- --run; fi
	@echo "8. Checking the synthetic data generator (docs/18 §7)..."
	@if [ -f tools/synthetic/pyproject.toml ]; then cd tools/synthetic && uv run ruff check . && uv run pyright && uv run pytest -q; fi
	@echo "==> All gates passed."

test: ## Run unit and integration tests
	cd backend && uv run pytest

test-visual: ## Run Playwright visual regression tests
	cd frontend && npm run test:visual

storybook-build: ## Build Storybook static assets
	cd frontend && npm run build-storybook

synth: ## Generate S1–S5 × seeds 1–5, S1 scanned, the fixtures and the demo set (docs/18)
	@echo "==> Generating synthetic scenarios..."
	cd tools/synthetic && uv run kredibel-synth generate --all --seeds 1-5 --out out
	cd tools/synthetic && uv run kredibel-synth generate --scenario S1 --seed 1 --scan --out out
	cd tools/synthetic && uv run kredibel-synth fixtures --out out/fixtures
	cd tools/synthetic && uv run kredibel-synth demo --out out/demo

gen-api: ## Regenerate frontend TypeScript types from OpenAPI spec
	@echo "==> Generating frontend API types from contracts/openapi.yaml..."
	cd frontend && npm run gen:api

record: ## Record real extractor outputs for a scenario (e.g. make record SCENARIO=S2 SEED=1)
	@echo "==> Recording extractor output for scenario $(SCENARIO)..."
	cd backend && uv run python -m app.adapters.record --scenario=$(SCENARIO) --seed=$(SEED)

evals: ## Run model evaluations (DeepEval)
	@echo "==> Running model evals..."
	cd backend && uv run python -m evals.runner

deploy: ## Deploy to Cloud Run via Cloud Build
	@echo "==> Submitting Cloud Build for project $(PROJECT_ID)..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi; \
	COMMIT_SHA=$$(git rev-parse --short HEAD 2>/dev/null || echo "latest"); \
	gcloud builds submit --config=cloudbuild.yaml \
		--substitutions=_COMMIT_SHA=$${COMMIT_SHA},_VITE_FIREBASE_API_KEY="$${VITE_FIREBASE_API_KEY}",_VITE_FIREBASE_AUTH_DOMAIN="$${VITE_FIREBASE_AUTH_DOMAIN}",_VITE_FIREBASE_PROJECT_ID="$${VITE_FIREBASE_PROJECT_ID}",_VITE_FIREBASE_APP_ID="$${VITE_FIREBASE_APP_ID}"

deploy-hosting: ## Build frontend and deploy to Firebase Hosting (kredibel-app)
	@echo "==> Building frontend for production..."
	cd frontend && npm run build
	@echo "==> Deploying to Firebase Hosting (kredibel-app)..."
	firebase deploy --only hosting --project $(PROJECT_ID)

tokens: ## Regenerate CSS from design tokens
	python3 tools/design/build_tokens.py

tokens-check: ## Check contrast and tokens
	python3 tools/design/build_tokens.py --check

mocks: ## Regenerate HTML mocks from tools/design/mocks/
	python3 tools/design/mocks/build_mocks.py

mock-shots: ## Take screenshots of HTML mocks for docs
	uv run --with playwright --with pillow python tools/design/shoot_mocks.py

dev-agents: ## Open the ADK dev UI on every workflow and agent (http://localhost:8501, docs/23)
	cd backend && PYTHONPATH=. uv run adk web --port 8501 --reload_agents app/agents/dev_apps

migrate-dry: ## Dry-run pending data migrations
	@if [ "$(ENV)" = "local" ]; then \
		cd backend && uv run python -m migrations run --dry-run; \
	else \
		gcloud run jobs execute kredibel-migrate --args=-m,migrations,run,--dry-run --region=$(REGION) --wait; \
	fi

migrate: ## Execute pending data migrations
	@if [ "$(ENV)" = "local" ]; then \
		cd backend && uv run python -m migrations run; \
	else \
		gcloud run jobs execute kredibel-migrate --args=-m,migrations,run --region=$(REGION) --wait; \
	fi

migrate-status: ## Check migration status
	@if [ "$(ENV)" = "local" ]; then \
		cd backend && uv run python -m migrations status; \
	else \
		gcloud run jobs execute kredibel-migrate --args=-m,migrations,status --region=$(REGION) --wait; \
	fi

schema-snapshot: ## Regenerate Firestore data schema snapshot
	python3 tools/checks/schema_drift.py --write
