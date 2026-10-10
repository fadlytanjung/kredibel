# 13 — Design Patterns & Conventions

> How code is organized and written, so that every feature looks like it was written by one person.
> Coding agents follow this page through `.agents/rules/`.

---

## 1. Repository layout

```
kredibel/
├── AGENTS.md                     agent workspace context (read first)
├── README.md
├── Makefile                      setup · dev · check · test · evals · synth · gen-api · deploy
├── Dockerfile                    multi-stage: frontend build → backend runtime (one image)
├── cloudbuild.yaml               test → build → push → deploy web + worker
├── contracts/                    normative, machine-readable contracts
│   ├── openapi.yaml
│   ├── firestore.rules
│   ├── firestore.indexes.json
│   ├── plans.v1.yaml             plan catalog, limits, features, UI languages, override bounds
│   └── policy/                   scorecard, categorization rules, forensics thresholds
├── backend/
│   ├── pyproject.toml · uv.lock
│   ├── app/
│   │   ├── main.py               create_app(settings, deps) — mounts routers by APP_ROLE
│   │   ├── core/                 settings, logging, errors (problem+json), auth, ids, clock, money
│   │   ├── domain/               PURE: models, enums, normalize, page_triage, verify, consensus,
│   │   │                         forensics/, metrics, reconciliation, counterparties,
│   │   │                         profile_suggestions, accounts, scorecard, grounding, case_state,
│   │   │                         plans, policy loader
│   │   ├── ports/                typing.Protocol interfaces for every external dependency
│   │   ├── adapters/             firestore_repo, gcs_store, cloud_tasks_queue, docai_ocr,
│   │   │                         docai_parser (P1), gemini_gateway, model_armor_shield,
│   │   │                         pdf_inspector, page_renderer, firebase_identity
│   │   ├── agents/
│   │   │   ├── workflows/        case_pipeline.py
│   │   │   ├── nodes/            doc_nodes.py, case_nodes.py (factories)
│   │   │   ├── llm/              Agent definitions + output schemas
│   │   │   ├── prompts/          *.md (front matter + text). No prompts in Python.
│   │   │   ├── tools/            case_tools.py (assistant, read-only)
│   │   │   ├── callbacks.py
│   │   │   └── deps.py           PipelineDeps dataclass
│   │   ├── services/             workspace, entitlement, applicant, case, document, analysis,
│   │   │                         review, assistant (use cases)
│   │   └── api/                  routers: health, me, plans, workspace, applicants, cases,
│   │                             documents, analysis, findings, transactions, invoices,
│   │                             counterparties, memo, decision, events, assistant, tasks
│   ├── tests/
│   │   ├── unit/                 domain + services with fakes
│   │   ├── integration/          API via httpx AsyncClient + fakes; Firestore emulator (optional)
│   │   ├── scenarios/            pipeline on synthetic scenarios with fake LLM/DocAI (recorded)
│   │   └── fakes/                in-memory implementations of every port
│   ├── evals/                    real-model evals (not in merge gate)
│   └── scripts/                  create_processors.py, set_claims.py, seed_demo_workspace.py,
│                                 seed_demo.py, reset_demo.py
├── frontend/
│   ├── package.json · package-lock.json · vite.config.ts · tsconfig.json
│   └── src/                      Feature-Sliced Design ([`11`](11-frontend.md) §3)
├── tools/
│   ├── synthetic/                document generator, scenarios, ground truth ([`18`](18-synthetic-data.md))
│   └── checks/                   repo checks: no long prompts in Python, status doc in sync
├── infra/
│   ├── bootstrap.sh              idempotent gcloud setup
│   ├── firebase.json · .firebaserc
│   ├── model-armor-template.json
│   └── ar-cleanup.json           Artifact Registry cleanup policy (cost)
├── docs/                         ALL spec-driven documents
│   ├── 00-…20-*.md               constitution, PRD, architecture, design, plans
│   ├── adr/                      architecture decision records
│   ├── diagrams/                 *.drawio.svg (SVG with the editable draw.io diagram embedded)
│   ├── specs/NNN-*/              feature specs: spec.md, plan.md, tasks.md
│   └── submission/               proposal, demo script, checklist
└── .agents/ (rules, skills)
```

---

## 2. Backend architecture rules

### 2.1 Layers and allowed imports

| Layer | May import | Must not |
|---|---|---|
| `domain` | stdlib, pydantic, `domain.*` | anything else (no Google SDKs, no FastAPI, no ADK, no I/O, no clock) |
| `ports` | `domain` | adapters, SDKs |
| `adapters` | `ports`, `domain`, `core`, Google/OSS SDKs | `services`, `api`, `agents` |
| `services` | `domain`, `ports`, `core` | `adapters` (injected instead), `api` |
| `agents` | `domain`, `ports`, `core`, ADK, google-genai types | `adapters` (injected), `api` |
| `api` | `services`, `core`, `domain` (schemas) | `adapters`, `agents` directly (except `api/tasks.py` → `services.analysis`) |
| `main.py` | everything (composition root) | — |

Enforced with **import-linter** contracts in `backend/.importlinter`; `make check` fails on a violation.

### 2.2 Patterns we use, and where

| Pattern | Where | Why |
|---|---|---|
| **Ports & adapters (hexagonal)** | `ports/` + `adapters/` | Swap Document AI/Gemini/Firestore for fakes in tests; keep Google SDK quirks out of domain code |
| **Composition root + DI** | `main.create_app(settings, deps)`, `agents.workflows.build_case_pipeline(deps)` | No globals; tests build the app with fakes |
| **Repository** | `adapters/firestore_repo.py` behind `CaseRepository` | One place that knows Firestore paths, minor units and chunked batches |
| **Value objects** | `Money`, `BBox`, `DateRange`, `Provenance` | Make invalid states unrepresentable (no float money, no unnormalized boxes) |
| **Strategy + registry** | forensic checks (`Check` protocol); page witnesses (`TextLayerWitness`, `OcrWitness`) chosen per page by triage | Add a check = add a class + register + enable in policy YAML; add a witness without touching the verifier |
| **Pipeline of idempotent nodes** | ADK workflow nodes | Retries and resumes never duplicate data ([`06`](06-agent-design.md) §7) |
| **Explicit state machine** | `domain/case_state.py` | All case transitions and guards in one tested table |
| **Policy as configuration** | `contracts/policy/*.yaml` + `domain/policy.py` loader; `contracts/plans.v1.yaml` + `domain/plans.py` | Risk rules and plan limits are reviewable data; the effective policy is hashed per run |
| **Specification (entitlements)** | `domain/plans.py` check functions return `Allowed` or `Denied(code, limit, used, max)` | One pure place for every limit; services call it inside the transaction that meters usage |
| **Suggest, then accept** | `domain/profile_suggestions.py` + `ApplicantService.decide_suggestion` | AI output never writes the profile directly; the analyst's decision does |
| **Anti-corruption layer** | `adapters/docai_ocr.py` / `docai_parser.py` mappers, `domain/normalize.py` | Raw reader shapes never leak beyond the adapter |
| **Gateway** | `GeminiGateway` port | One place for model calls: schema enforcement, retries, labels, quarantine check, usage accounting |
| **Domain errors → problem+json** | `core/errors.py` | Stable error `code`s, one exception handler |
| **Atomic audit** | Repository methods that change state also append the event in the same Firestore transaction | No state change without its audit event |

### 2.3 Python conventions

- Python 3.12; `uv` for everything (`uv sync`, `uv run`).
- Type-checked with **pyright (strict)** on `app/`; `ruff` for lint + format (line length 100).
- `async` for all I/O. Sync SDKs (Storage, pikepdf, pdfplumber, pypdfium2) run in a thread via
  `anyio.to_thread.run_sync`. Use async clients where they exist (Firestore `AsyncClient`, Document AI
  and Cloud Tasks async clients).
- **No `float` for money.** `Decimal` only; the ruff rule set includes a custom check (`tools/checks`)
  that flags `float(` in `domain/`.
- **No `datetime.now()`** outside `core/clock.py`; inject `Clock`.
- Pydantic v2 models for every boundary (API, LLM output, Firestore documents). `model_config =
  ConfigDict(frozen=True)` for domain value objects.
- Logging via `structlog` (JSON). Always bind `case_id`, `run_id`, `node`. Never log document text,
  descriptions, names or account numbers.
- Comments explain *why*. A guard's comment names the failure it prevents.
- Files ≤ 400 lines; functions ≤ 50 lines as a guideline. Split by responsibility, not by line count.
- Prompts live in `agents/prompts/*.md`. **No prompt string > 200 characters in Python**
  (`tools/checks/no_long_prompts.py`).

### 2.4 Error handling

| Situation | Behaviour |
|---|---|
| Invalid input at the API | Pydantic → `422 VALIDATION_ERROR` with field errors |
| Business rule violated | Raise a `DomainError` subclass with a `code`; mapped to 409/403/422 |
| External call transient failure | Retry in the adapter (bounded, jittered); then raise `ExternalServiceError` |
| Node failure inside a document | Mark the document `FAILED` + finding `E02`; continue the case |
| Unexpected error | Log with stack; respond `500 INTERNAL` with a generic detail |

---

## 3. Frontend conventions

- TypeScript `strict`, `noUncheckedIndexedAccess`; **no `any`** (lint error).
- Named exports only. One component per file; file name = component name.
- Server data only through TanStack Query hooks in `entities/*/api.ts`; no `fetch` in components.
- Forms: react-hook-form + zod; zod schemas derived from the OpenAPI types where possible.
- Styling: Tailwind utilities with design tokens only; inline styles only for computed geometry
  (bbox overlays, chart sizes).
- All user-visible strings in `shared/i18n/locales/en/*.json`, read with `useTranslation()`;
  ESLint `i18next/no-literal-string` enforces it. Another language later is a new folder, not a
  refactor. English is the only selectable language today.
- Plan-limited actions show the limit before the user hits it (`UsageMeter`, disabled reasons); the
  server's `403` is still handled everywhere.
- Money and dates only through `MoneyText`/`DateText`/`formatMoney`/`formatDate`.
- Markdown rendering only through `shared/ui/SafeMarkdown` (no raw HTML).

---

## 4. Cross-cutting conventions

| Topic | Convention |
|---|---|
| Time zone | Store UTC instants; display in the browser's zone. Document dates are local calendar dates (no zone). |
| IDs | Prefixed ULIDs (`case_…`); deterministic content IDs per [`09`](09-data-model.md) §4 |
| Feature flags | Env vars `FEATURE_MODEL_ARMOR`, `FEATURE_VISUAL_FORENSICS`, `FEATURE_REVISION_DIFF`, `FEATURE_ASSISTANT` (default off until the P1 spec is done) |
| Personal data | Never log names, addresses, account or ID numbers; account numbers only as mask (`••••1234`) in readable data and as a hash in `orgPrivate/`; ID numbers only as the last 4 digits |
| Plans and limits | Never hard-code a limit; read effective limits from `EntitlementService`. Plan-specific behaviour is a plan **feature** flag in `plans.v1.yaml`, not an `if plan == …` |
| Language | API and LLM output in English; error `code`s are the stable contract for localization |
| Configuration | Env vars only, validated at startup by `Settings`; no config files except policy YAML |
| Secrets | None needed (ADC everywhere). If one appears, it goes in Secret Manager and is mounted as an env var. |
| Diagrams | Mermaid inside markdown for flows that change with the text; draw.io `.drawio.svg` in `docs/diagrams/` (edited with the VS Code draw.io extension) for architecture, swimlanes, lineage and wireframes. Update a diagram in the same commit as the behaviour it shows. |

---

## 5. Testing conventions

- Test names state the behaviour and the requirement:
  `test_fr044_approve_is_blocked_while_a_critical_finding_is_open`.
- Every port has an in-memory fake in `tests/fakes/`; unit and integration tests never touch the
  network.
- Domain tests use builders (`StatementBuilder().with_rows(...).tamper_row(5, credit="7250000")`).
- Scenario tests replay **recorded** Document AI and Gemini outputs for the synthetic scenarios
  (`tests/scenarios/recordings/`), so the full pipeline is tested deterministically and offline.
- Evals call real models and are run with `make evals` on demand ([`15`](15-testing-and-evaluation.md)).

---

## 6. Git & workflow

- One branch per spec: `feat/005-document-extraction`.
- Conventional Commits with the spec number as scope: `feat(005): merge consensus for statement rows`.
- Every commit references task IDs in the body: `Tasks: T005-07, T005-08`.
- PRs (or direct merges for a 2-person team) must pass `make check`.
- `docs/20-implementation-status.md` is updated in the same commit that changes a component's status.

---

## 7. Makefile targets

| Target | Does |
|---|---|
| `make setup` | `uv sync` (backend), `npm ci` (frontend), pre-commit hooks |
| `make dev` | Backend on :8000 with `APP_ROLE=all` (web + worker routes, in-process task runner) and Vite on :5173 with `/api` proxy |
| `make check` | ruff, pyright, import-linter, repo checks, pytest (unit + integration + scenarios), eslint, tsc, vitest |
| `make synth` | Generate synthetic scenarios into `tools/synthetic/out/` |
| `make gen-api` | Regenerate `frontend/src/shared/api/schema.d.ts` from `contracts/openapi.yaml` |
| `make evals` | Real-model evals; writes `backend/evals/reports/<date>.md` |
| `make deploy` | Submit `cloudbuild.yaml` |

`APP_ROLE=all` with `TASK_QUEUE=inline` lets local development run the worker in-process (an
`InlineTaskQueue` adapter calls the task handler directly). Cloud Tasks is used only in the cloud.
