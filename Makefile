# Kredibel Makefile — unified developer workflow
# Run `make help` to inspect available commands.

SHELL := /usr/bin/env bash
PROJECT_ID ?= cloud-hack2skill
REGION ?= asia-southeast1
SCENARIO ?= S1
SEED ?= 1
ENV ?= local

.PHONY: help setup dev check test synth gen-api record evals deploy env-keys env-pull env-push deploy-hosting tokens tokens-check mocks mock-shots dev-agents migrate migrate-dry migrate-status docker-up docker-down schema-snapshot

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

dev: ## Run local dev servers (FastAPI on :8000, Vite on :5173, Langfuse, Firestore emulator)
	@echo "Starting Kredibel in local dev mode..."
	@if [ -f .env ]; then export $$(cat .env | grep -v '^#' | xargs); fi
	@make docker-up
	@if [ -f infra/langfuse/docker-compose.yml ]; then \
		echo "Ensuring Langfuse trace viewer is running..."; \
		make langfuse-up; \
	fi
	@echo ""
	@echo "==================================================================="
	@echo "  Kredibel Local Development Services"
	@echo "==================================================================="
	@echo "  • Web App (Frontend):     http://localhost:5173"
	@echo "  • Backend API:            http://localhost:8000"
	@echo "  • API Docs (Swagger):     http://localhost:8000/docs"
	@echo "  • API Docs (ReDoc):       http://localhost:8000/redoc"
	@echo "  • Langfuse Traces:        http://localhost:3000"
	@echo "  • Firestore Emulator:     http://localhost:8080 (UI: :4000)"
	@echo "  • AI Content Capture:     $(if $(CONTENT),ENABLED (prompts & responses visible),OFF (metadata only; pass CONTENT=1))"
	@echo "==================================================================="
	@echo ""
	@npx -y concurrently -n "api,web" -c "cyan,magenta" \
		"$(if $(filter 1,$(NO_LANGFUSE)),,$(WITH_LANGFUSE)) AI_CONTENT_CAPTURE=$(if $(CONTENT),synthetic,off) DATA_CLASS=$(if $(CONTENT),synthetic,$${DATA_CLASS:-real}) make dev-backend" \
		"make dev-frontend"

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
	@python3 tools/checks/mock_sync.py
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

deploy: ## Deploy to Cloud Run via Cloud Build (configuration: the kredibel-env secret, ADR-024)
	@test -z "$$(git status --porcelain --untracked-files=no)" || { echo "Commit first: the build must match a commit"; exit 1; }
	@echo "==> Submitting Cloud Build for project $(PROJECT_ID)..."
	gcloud builds submit --project=$(PROJECT_ID) --config=cloudbuild.yaml \
		--substitutions=_COMMIT_SHA=$$(git rev-parse --short HEAD)

env-keys: ## List which keys .env.production sets, never their values
	@infra/env-secret.sh keys .env.production

env-pull: ## Write the latest kredibel-env secret to .env.production
	@PROJECT_ID=$(PROJECT_ID) infra/env-secret.sh pull .env.production

env-push: ## Add a kredibel-env version from .env.production (then make deploy)
	@PROJECT_ID=$(PROJECT_ID) infra/env-secret.sh push .env.production

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

.PHONY: trace-up trace-down trace-smoke dev-traced
trace-up: ## Start local OTel collector and viewer (http://localhost:16686)
	docker compose --profile tracing up -d jaeger

trace-down: ## Stop the local trace viewer (clears transient traces)
	docker compose --profile tracing stop jaeger

trace-smoke: ## Send a synthetic trace and verify it appears in the local viewer
	cd backend && ENV_FILE=/dev/null PYTHONPATH=. uv run python scripts/trace_smoke.py

dev-traced: ## Run the local API/inline worker with metadata traces in Jaeger
	TRACE_EXPORT=otlp AI_CONTENT_CAPTURE=off $(MAKE) dev-backend

.PHONY: langfuse-up langfuse-down langfuse-smoke dev-langfuse gemini-usage
LANGFUSE_COMPOSE := docker compose -f infra/langfuse/docker-compose.yml --env-file infra/langfuse/.env
# The project keys from infra/langfuse/.env, for commands that send traces to the local Langfuse.
WITH_LANGFUSE := set -a && . ./infra/langfuse/.env && export TRACE_EXPORT=langfuse LANGFUSE_HOST=http://127.0.0.1:3000 && set +a

langfuse-up: ## Start a local Langfuse at http://localhost:3000 (ADR-026); the first run writes infra/langfuse/.env
	python3 tools/langfuse/init_env.py
	$(LANGFUSE_COMPOSE) up -d --wait
	@echo "Langfuse: http://localhost:3000  (sign in as dev@kredibel.local; the password is LANGFUSE_INIT_USER_PASSWORD in infra/langfuse/.env)"

langfuse-down: ## Stop the local Langfuse; its traces stay (RESET=1 deletes them)
	$(LANGFUSE_COMPOSE) down $(if $(RESET),-v,)

langfuse-smoke: ## Send a synthetic trace with one generation to the local Langfuse and find it
	$(WITH_LANGFUSE) && cd backend && ENV_FILE=/dev/null PYTHONPATH=. uv run python scripts/trace_smoke.py --langfuse

dev-langfuse: ## Run the local API/inline worker traced in Langfuse (CONTENT=1: prompts too; refused unless DATA_CLASS=synthetic)
	$(WITH_LANGFUSE) && export AI_CONTENT_CAPTURE=$(if $(CONTENT),synthetic,off) DATA_CLASS=$(if $(CONTENT),synthetic,$${DATA_CLASS:-real}) && $(MAKE) dev-backend

gemini-usage: ## Gemini requests and tokens of the project from Cloud Monitoring (DAYS=7)
	cd backend && PYTHONPATH=. uv run python scripts/gemini_usage.py --days $(or $(DAYS),7)

.PHONY: demo-books demo-account demo-template video video-silent extractions-rebuild reread-photos clean-workspace
clean-workspace: ## Clean up workspace documents, bank lines and runs (EMAIL=... or ORG=...)
	cd backend && uv run python -m scripts.clean_workspace $(if $(EMAIL),--email "$(EMAIL)",) $(if $(ORG),--org "$(ORG)",)

demo-books: ## Upload synthetic demo books into EMAIL's workspace (docs/18 §5; DRY=1, MONTHS=..., CLEAN=1, SCENARIOS=...)
	$(if $(filter 1,$(NO_LANGFUSE)),,$(WITH_LANGFUSE) && export DATA_CLASS=synthetic AI_CONTENT_CAPTURE=$(if $(NO_CONTENT),off,synthetic) &&) cd backend && $(shell command -v caffeinate >/dev/null && echo caffeinate -i) uv run python -m scripts.upload_demo_books --email "$(EMAIL)" $(if $(DRY),--dry-run,) $(if $(MONTHS),--months "$(MONTHS)",) $(if $(SCENARIOS),--scenarios "$(SCENARIOS)",) $(if $(filter 1,$(CLEAN)),--clean,)

extractions-rebuild: ## Rebuild a workspace's chunks and page Markdown from what is stored, no model call (spec 022; ORG=... or EMAIL=...)
	cd backend && uv run python -m scripts.rebuild_extractions $(if $(ORG),--org "$(ORG)",--email "$(EMAIL)")

reread-photos: ## Read a workspace's photos and scans again with the OCR witness (spec 022; ORG=..., DISAGREED=1 also those whose fields did not all agree, ALL=1 every OCR document)
	cd backend && uv run python -m scripts.reread_documents --org "$(ORG)" $(if $(DISAGREED),--disagreed,) $(if $(ALL),--ocr,)

video: ## The demo video (tools/video): voice the narration with Cloud Text-to-Speech, record it on production with the demo account (resets it), cut it (VIDEO_OWNER_EMAIL=... adds the Google onboarding scene)
	cd backend && uv run python ../tools/video/narrate.py
	cd tools/synthetic && uv run kredibel-synth demo --shift-months 5 --per-month 100 --out out/demo-shift5 >/dev/null
	cd frontend && VIDEO_OWNER_TOKEN="$$($(if $(VIDEO_OWNER_EMAIL),cd ../backend && uv run python -m scripts.custom_token --email $(VIDEO_OWNER_EMAIL),true))" npx playwright test -c playwright.video.config.ts
	python3 tools/video/edit.py

video-silent: ## The demo video without captions or sound, to dub over (tools/video): records it again on production, writes kredibel-demo-silent.mp4 and its .srt (VIDEO_OWNER_EMAIL=... adds the Google onboarding scene)
	cd backend && uv run python ../tools/video/narrate.py
	cd tools/synthetic && uv run kredibel-synth demo --shift-months 5 --per-month 100 --out out/demo-shift5 >/dev/null
	cd frontend && VIDEO_CAPTIONS=0 VIDEO_FRAMES=frames-silent VIDEO_OWNER_TOKEN="$$($(if $(VIDEO_OWNER_EMAIL),cd ../backend && uv run python -m scripts.custom_token --email $(VIDEO_OWNER_EMAIL),true))" npx playwright test -c playwright.video.config.ts
	python3 tools/video/edit.py --silent

demo-account: ## Create or reset the public demo account (spec 024; DEMO_ACCOUNT_EMAIL=..., DEMO_ACCOUNT_PASSWORD=...)
	cd backend && DEMO_ACCOUNT_EMAIL="$(DEMO_ACCOUNT_EMAIL)" DEMO_ACCOUNT_PASSWORD="$(DEMO_ACCOUNT_PASSWORD)" uv run python -m scripts.demo_account

demo-template: ## Build the demo template workspace (spec 021): seed it, then read the demo books ending last month (TEMPLATE_EMAIL=..., RETRY=1 reads failed documents again)
	cd tools/synthetic && uv run kredibel-synth demo --shift-months 5 --window 2026-08:2026-10 --pack --per-month 100 --out out/demo-aug-oct
	cd backend && uv run python -m scripts.seed_demo_workspace --org org_demo_template --name "Sunrise Coffee Roasters" --entity COMPANY --trial-ends 2027-12-31 --timezone Asia/Jakarta --owner "$(or $(TEMPLATE_EMAIL),template@demo.kredibel)" --database "$${FIRESTORE_DATABASE:-kredibel}"
	cd backend && DATA_CLASS=synthetic AI_CONTENT_CAPTURE=off $(shell command -v caffeinate >/dev/null && echo caffeinate -i) uv run python -m scripts.upload_demo_books --email "$(or $(TEMPLATE_EMAIL),template@demo.kredibel)" --demo-dir ../tools/synthetic/out/demo-aug-oct/pack --concurrency 10 $(if $(RETRY),--retry-failed,)

.PHONY: demo-reconciliation demo-reconciliation-traced reconciliation-fixtures
demo-reconciliation: ## Replay generated invoices/receipts/statements in both orders (offline)
	cd backend && ENV_FILE=/dev/null PYTHONPATH=. uv run python scripts/demo_reconciliation.py

demo-reconciliation-traced: ## Replay generated documents with traces at http://localhost:16686
	cd backend && ENV_FILE=/dev/null PYTHONPATH=. uv run python scripts/demo_reconciliation.py --trace

reconciliation-fixtures: ## Regenerate the five S1 PDFs used by the offline reconciliation replay
	cd tools/synthetic && uv run python reconciliation_fixtures.py

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
