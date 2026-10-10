# Tasks 001 — Foundation

Legend: `[ ]` to do · `[P]` parallel with the previous task · **TDD** = write the test first and see it fail.
Each task lists the acceptance criteria it serves.

## Phase 1 — Repository & tooling

- [ ] **T001-01** Create the repository layout of [`docs/13`](../../13-design-patterns-and-conventions.md) §1 (empty packages with `__init__.py`), `.gitignore` (incl. `tools/synthetic/out/` except `demo/`), `Makefile` with all targets as stubs.
- [ ] **T001-02** `backend/pyproject.toml` + `uv lock`; ruff + pyright config; `.importlinter` contracts. (AC-001-11, AC-001-13)
- [ ] **T001-03** [P] Frontend: `npm create vite` (React + TS), Tailwind v4, ESLint (incl. `eslint-plugin-boundaries`), Vitest + Testing Library + MSW, `theme.css` tokens. (AC-001-1)
- [ ] **T001-04** `tools/checks/no_long_prompts.py` (**TDD**: fixture file with a 201-char literal fails) and `tools/checks/scan_secrets.py`; wire into `make check`. (AC-001-12)
- [ ] **T001-05** `make check` runs every gate in order and fails fast. (AC-001-11)

## Phase 2 — Backend core

- [ ] **T001-06** **TDD** `core/settings.py` validation (missing required vars fail at startup; `APP_ROLE` enum).
- [ ] **T001-07** `core/errors.py` + handlers; **TDD** a raised `DomainError` renders RFC 9457 with `code`.
- [ ] **T001-08** `core/logging.py` JSON logging + request middleware.
- [ ] **T001-09** **TDD** `core/auth.py`: missing header → 401, bad token → 401, no `orgId` → `Principal(org_id=None)` (routes that need a workspace → `403 WORKSPACE_REQUIRED`), valid → `Principal`. Fake verifier injected through `deps`. (AC-001-4, AC-001-5)
- [ ] **T001-10** `api/health.py` and `api/me.py`; `main.create_app` mounting by role; **TDD** `/tasks/*` absent on `web`, `/api/me` absent on `worker`. (AC-001-1, AC-001-6, AC-001-10)
- [ ] **T001-11** `core/security_headers.py`; test that headers are present. 
- [ ] **T001-12** `api/static.py`: SPA fallback for non-`/api` paths (web/all).
- [ ] **T001-13** `scripts/set_claims.py` (sets claims, upserts member doc, prints result).

## Phase 3 — Frontend shell

- [ ] **T001-14** `shared/firebase/app.ts`, `AuthProvider`, `LoginPage` (email/password + Google), sign-out. (AC-001-3, AC-001-7)
- [ ] **T001-15** `shared/api/client.ts` with problem parsing and 401 → sign-out; **TDD** with MSW. (AC-001-5)
- [ ] **T001-16** Router with protected routes; `CaseListPage` empty state; redirect to the `/onboarding` placeholder when `needsWorkspace`. (AC-001-3, AC-001-4)
- [ ] **T001-25** i18n scaffold: i18next + react-i18next, `locales/en/common.json`, `useTranslation` in the shell, `eslint-plugin-i18next` rule, `Intl`-based `formatMoney`/`formatDate`. (AC-001-14)
- [ ] **T001-17** Vite dev proxy `/api → :8000`. (AC-001-2)

## Phase 4 — Cloud

- [ ] **T001-18** `infra/bootstrap.sh` exactly as [`docs/16`](../../16-infrastructure-and-deployment.md) §3 (idempotent; `|| true` on creates). Run it.
- [ ] **T001-19** `Dockerfile` multi-stage; build locally and run with `APP_ROLE=all`.
- [ ] **T001-20** `cloudbuild.yaml` (check → build → push → deploy worker → deploy web → smoke); `infra/env.*.yaml`. (AC-001-8)
- [ ] **T001-24** Cost guardrails from docs/21 §7: budget with 50/90/100% alerts, `infra/ar-cleanup.json` (keep 3 most recent images) applied, `RUNS_ENABLED`/`RUN_QUOTA_PER_ORG_PER_DAY` in `infra/env.web.yaml`.
- [ ] **T001-21** First deploy; grant `run.invoker` to `kredibel-tasks-invoker`; add the web URL to Firebase authorized domains; create demo users with `set_claims.py`.
- [ ] **T001-22** Verify AC-001-9 (`curl` worker without token → 403) and AC-001-3 on the deployed URL.

## Phase 5 — Close

- [ ] **T001-23** Update `docs/20-implementation-status.md` (foundation rows → Built) and `README.md` quick start.
