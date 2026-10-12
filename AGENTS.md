# Kredibel — agent guide

Kredibel is an AI finance workspace that checks a small business's own books. A business (or a
person) signs up as a **workspace** (free trial; paid tiers and a loan readiness report coming soon)
and uploads bank statements, sales and purchase invoices, receipts and general-ledger exports **in any
order**. Exact copies are recorded and never read; ADK workflows on Cloud Run parse every page into
layout chunks (the PDF text layer, or Document AI OCR for scans and photos), read it with Gemini from
the image plus those chunks, and **ground** every value in the words of the chunk it cites (ADR-023),
import ledger files by code with a mapping the user confirms once, hold
**content duplicates** until a person decides, run deterministic **forensics**, and **reconcile each
month** from all its data (same result whatever the upload order). What AI cannot match goes to a
**review queue**; each month and document gets a **fraud risk level** with evidence and next steps
explained by Gemini; a dashboard shows where the money went (Sankey). A Finance Assistant (P1)
answers questions with read-only tools, retrieval and Memory Bank. Every classification and category
is a **label** people can confirm or correct (P1), and every run is traced in Cloud Trace and, in P1,
BigQuery. The UI is English.

This file is the shared context for any coding agent working in this repository. Always-on rules live
in `.agents/rules/`; repeatable procedures live in `.agents/skills/` (invoke with `/<skill-name>`).

## Where the truth lives

| Need | Read |
|---|---|
| Principles every change must respect | `docs/00-constitution.md` |
| What to build next | `docs/specs/README.md`, then `docs/specs/NNN-*/tasks.md` |
| Why and how | the `spec.md` / `plan.md` of that spec and the docs they link |
| API shapes | `contracts/openapi.yaml` (authoritative) |
| Data shapes | `docs/09-data-model.md`, `contracts/firestore.rules`, `contracts/firestore.indexes.json` |
| Changing a data shape | `docs/22-data-migrations.md` (versions, upcasters, migrations) and the `/data-migration` skill |
| Risk rules, thresholds, categories per accounting framework, label policy | `contracts/policy/*.yaml` (never hard-code these) |
| Plans, limits, UI languages | `contracts/plans.v1.yaml` (never hard-code a limit) |
| Code layout and patterns | `docs/13-design-patterns-and-conventions.md` |
| What is already built | `docs/20-implementation-status.md` |
| Pictures of the system | `docs/diagrams/*.drawio.svg` (index in `docs/README.md`) |
| How screens look and respond (360–1600 px) | `docs/12-design-system.md`, `contracts/design/tokens.json`, mocks in `design/mocks/` |

If code and docs disagree, **stop and fix the doc first** (or ask), then change the code.

## How to work

1. Pick the first unchecked task of the current spec (`/sdd-implement-task`).
2. For tasks marked **TDD**: write the failing test, run it, see it fail for the right reason.
3. Make the smallest change that passes; run `make check`.
4. Tick the task in `tasks.md`; commit `feat(NNN): <what>` with `Tasks: TNNN-xx` in the body.
5. When a component changes status, update `docs/20-implementation-status.md` in the same commit.
6. Never work on two specs in one change. Never start P1 work before the P0 path runs on Cloud Run.

## Commands

Created by spec 001. Until then, start with `docs/specs/001-foundation/tasks.md`.

| Task | Command |
|---|---|
| Install everything | `make setup` |
| Run locally (API :8000 with in-process worker, Vite :5173) | `make dev` |
| All gates (lint, types, layers, repo checks, tests) | `make check` |
| Generate synthetic scenarios | `make synth` |
| Regenerate frontend API types | `make gen-api` |
| Record real extractor outputs for a scenario | `make record SCENARIO=S2 SEED=1` |
| Real-model evals (not a gate) | `make evals` |
| Deploy via Cloud Build | `make deploy` |
| Regenerate CSS from the design tokens (and check contrast) | `make tokens` |
| Regenerate the HTML mocks from `tools/design/mocks/` | `make mocks` |
| Screenshot the HTML mocks for the docs | `make mock-shots` |
| Debug an LLM node or the assistant in the ADK dev UI | `make dev-agents` (`LIVE=1` for real Gemini) |
| Data migrations: dry run, run, status | `make migrate-dry ENV=…`, `make migrate ENV=…`, `make migrate-status ENV=…` |

Backend uses **uv** (`uv sync`, `uv run`; commit `uv.lock`). Frontend uses **npm** (commit
`package-lock.json`). The synthetic generator is its own uv project in `tools/synthetic/`.

## Architecture in one screen

```
Browser (React SPA, Firebase Auth) ──HTTPS + ID token──▶ Firebase Hosting (SPA) ──/api/**──▶ kredibel-web (Cloud Run: /api + SPA)
      │ Firestore listeners (documents, months, runs)          │ plan checks, SHA-256 duplicates,
      │                                                       │ page split, review actions,
      │                                                       │ Finance Assistant (P1)
      ▼                                                       ▼ tasks: doc-{docId}-n, month-{org}-{yyyy-mm}-{gen}
   Firestore ◀──────────── writes ─────────────── kredibel-worker (Cloud Run, IAM-only)
   Cloud Storage ◀────────────────────────────────  ADK document_workflow and month_workflow
                                                    ├─ Gemini (global): readers, mapper, explainer
                                                    ├─ Document AI OCR (us): witness for scans
                                                    ├─ Model Armor (P1)
                                                    └─ pure domain code: verifier, duplicates,
                                                       forensics, reconcile_month, risk, money flow
```

Full picture with Google Cloud icons: `docs/diagrams/gcp-architecture.drawio.svg`.

Backend layers: `api → services/agents → domain + ports`; `adapters` implement `ports`; `domain` is
pure (no I/O, no SDKs, no clock). Enforced by import-linter.

## Non-negotiables

1. **Numbers come from code.** Models never compute money, matches, risk levels or totals.
2. **Every claim has evidence.** Findings and matches carry evidence refs and reasons; explanations and
   assistant answers carry citations and pass the grounding guard.
3. **Documents are adversarial.** Document content is data, never instructions. Assistant tools are
   read-only and workspace-scoped. Quarantined documents never reach a model.
4. **Grounded values before an accusation.** CRITICAL arithmetic findings only on values grounded in
   the page's own words (`AGREED`). The AI reader gets the page image plus numbered layout chunks and
   cites the chunk of every value; code, not the model, decides whether it is found there (ADR-023).
5. **A person resolves the exceptions.** Only unique, high-scoring matches are automatic; everything
   else is a review item. User decisions are inputs to reconciliation and are never undone by a re-run.
   Possible duplicates are held, never deleted, until a person decides.
6. **Google Cloud only** for managed services and AI. Open-source libraries inside our containers are fine.
7. **Real documents in production, synthetic everywhere else** (ADR-022). Tests, fixtures, evals,
   mocks and the repository use synthetic data only; real documents are never committed, and their
   content, names and account numbers never appear in logs, traces, tool output or commits.
8. **No secrets** in the repo, image, logs or tool output. Google access uses service accounts (ADC).
9. **Money is `Decimal`** (Python) / integer minor units (Firestore) / decimal strings (JSON). Never float.
10. **Prompts live in `backend/app/agents/prompts/*.md`.** No prompt text over 200 characters in Python.
11. **The AI suggests, the user accepts.** Nothing the models detect is written to the workspace's
    profile, a ledger mapping or a match without a person's decision.
12. **Limits are enforced on the server** from `contracts/plans.v1.yaml`; the UI only warns early.
13. **English UI, externalized strings.** No literal UI strings in components; personal data (account
    and ID numbers) is never logged and only stored masked.
14. **Design values come from tokens.** Colours, sizes, radii, shadows and durations live only in
    `contracts/design/tokens.json`; components use the generated variables; every screen works from
    360 px to 1600 px.
15. **Data changes are versioned.** Every document has `schemaVersion`; breaking changes go
    expand → migrate → contract with an upcaster and a forward-only migration; audit events are never
    rewritten.
16. **Same data, same result.** `reconcile_month` is pure over all of a month's data and decisions;
    the upload order never changes the outcome (property-tested).
17. **People's labels win; learning needs consent.** Every classification and category is a label;
    a model never overwrites a label a person confirmed or corrected. Verified examples in prompts come
    from the same workspace only; nothing leaves a workspace for tuning without the owner's consent,
    masked. Prompt and response content is recorded only with synthetic data (`AI_CONTENT_CAPTURE`).

## Configuration

All configuration is environment variables validated by `backend/app/core/settings.py`; the full list
is in `docs/16-infrastructure-and-deployment.md` §6. Model IDs are configuration (`MODEL_FAST`,
`MODEL_LITE`, `MODEL_EMBEDDING`), never literals in code. `VITE_*` values are public.

## Definition of done for a task

- Acceptance criteria referenced by the task are demonstrably met (test or documented manual check).
- `make check` is green.
- No new dependency without updating the spec's `plan.md`.
- Docs updated if behaviour, contracts or status changed.
