# Tasks 001 — Foundation

Legend: `[ ]` to do · `[P]` parallel with the previous task · **TDD** = write the test first and see it fail.
Each task lists the acceptance criteria it serves.

## Phase 1 — Repository & tooling

- [x] **T001-01** Create the repository layout of [`docs/13`](../../13-design-patterns-and-conventions.md) §1 (empty packages with `__init__.py`), `.gitignore` (incl. `tools/synthetic/out/` except `demo/`), `Makefile` with all targets as stubs.
- [x] **T001-02** `backend/pyproject.toml` + `uv lock`; ruff + pyright config; `.importlinter` contracts. (AC-001-11, AC-001-13)
- [x] **T001-03** [P] Frontend: `npm create vite` (React + TS), Tailwind v4, ESLint (incl. `eslint-plugin-boundaries`), Vitest + Testing Library + MSW. (AC-001-1)
- [x] **T001-04** `tools/checks/no_long_prompts.py` (**TDD**: fixture file with a 201-char literal fails) and `tools/checks/scan_secrets.py`; wire into `make check`. (AC-001-12)
- [x] **T001-05** `make check` runs every gate in order and fails fast. (AC-001-11)

## Phase 2 — Backend core

- [x] **T001-06** **TDD** `core/settings.py` validation (missing required vars fail at startup; `APP_ROLE` enum).
- [x] **T001-07** `core/errors.py` + handlers; **TDD** a raised `DomainError` renders RFC 9457 with `code`.
- [x] **T001-08** `core/logging.py` JSON logging + request middleware.
- [x] **T001-09** **TDD** `core/auth.py`: missing header → 401, bad token → 401, no `orgId` → `Principal(org_id=None)` (routes that need a workspace → `403 WORKSPACE_REQUIRED`), valid → `Principal`. Fake verifier injected through `deps`. (AC-001-4, AC-001-5)
- [x] **T001-10** `api/health.py` and `api/me.py`; `main.create_app` mounting by role; **TDD** `/tasks/*` absent on `web`, `/api/me` absent on `worker`. (AC-001-1, AC-001-6, AC-001-10)
- [x] **T001-11** `core/security_headers.py`; test that headers are present. 
- [x] **T001-12** `api/static.py`: SPA fallback for non-`/api` paths (web/all).
- [x] **T001-13** `scripts/set_claims.py` (sets claims, upserts member doc, prints result).

## Phase 3 — Frontend shell

- [x] **T001-14** `shared/firebase/app.ts`, `AuthProvider`, `LoginPage` (email/password + Google), sign-out. (AC-001-3, AC-001-7)
- [x] **T001-15** `shared/api/client.ts` with problem parsing and 401 → sign-out; **TDD** with MSW. (AC-001-5)
- [x] **T001-16** Router with protected routes for every route of [`docs/11`](../../11-frontend.md) §4 (placeholders); `DashboardPage` empty state; redirect to the `/onboarding` placeholder when `needsWorkspace`. (AC-001-3, AC-001-4)
- [x] **T001-25** i18n scaffold: i18next + react-i18next, `locales/en/common.json`, `useTranslation` in the shell, `eslint-plugin-i18next` rule, `Intl`-based `formatMoney`/`formatDate`. (AC-001-14)
- [x] **T001-17** Vite dev proxy `/api → :8000`. (AC-001-2)

## Phase 4 — Cloud

- [x] **T001-18** `infra/bootstrap.sh` exactly as [`docs/16`](../../16-infrastructure-and-deployment.md) §3 (idempotent; `|| true` on creates). Run it.
- [ ] **T001-19** `Dockerfile` multi-stage; build locally and run with `APP_ROLE=all`.
- [ ] **T001-20** `cloudbuild.yaml` (check → build → push → deploy worker → deploy web → smoke); `infra/env.*.yaml`. (AC-001-8)
- [ ] **T001-24** Cost guardrails from docs/21 §7: budget with 50/90/100% alerts, `infra/ar-cleanup.json` (keep 3 most recent images) applied, `RUNS_ENABLED`/`RUN_QUOTA_PER_ORG_PER_DAY` in `infra/env.web.yaml`.
- [ ] **T001-21** First deploy; grant `run.invoker` to `kredibel-tasks-invoker`; add the web URL to Firebase authorized domains; create demo users with `set_claims.py`.
- [ ] **T001-22** Verify AC-001-9 (`curl` worker without token → 403) and AC-001-3 on the deployed URL.

## Phase 4a — Design foundation

- [x] **T001-26** `make tokens` / `make tokens-check` wired to `tools/design/build_tokens.py`, and `make mocks` / `make mock-shots` to `tools/design/mocks/build_mocks.py` and `tools/design/shoot_mocks.py`; generated CSS imported by `app/styles`; Archivo via `@fontsource-variable/archivo`. (AC-001-15)
- [x] **T001-27** **TDD** `tools/checks/no_raw_styles.py` (fixtures: hex colour, `rgb(`, `[13px]`, `style=` outside the allow-list fail; tokens pass); add to `make check`. (AC-001-18)
- [x] **T001-28** `AppShell` (sidebar, rail, bottom nav with More sheet, top bar with Upload, dock) with `useSizeClass`; first `shared/ui` components with `cva`; matches the shell of `design/mocks/dashboard.html` at the three widths. (AC-001-16)
- [ ] **T001-29** Storybook 9 + a11y addon + test runner; one story per component state; Playwright visual tests for the shell and login at 390/834/1440 with committed baselines; CI job. (AC-001-17)

## Phase 4b — Data-migration foundation

- [x] **T001-30** **TDD** `adapters/firestore/upcast.py` registry and chain; `SchemaTooNewError`; sample `documents` model v1/v2 with fixtures. (AC-001-19)
- [x] **T001-31** **TDD** `backend/migrations/runner.py` with the emulator: paging, preconditions, checkpoint, dry run, lock lease, registry document; sample `0000_example`. (AC-001-20)
- [x] **T001-32** `make schema-snapshot` and `tools/checks/schema_drift.py`; commit `contracts/data/schema-snapshot.json`. (AC-001-21)
- [x] **T001-33** Bootstrap additions (backups bucket and lifecycle, PITR, backup schedule, `kredibel-migrate` SA and job); Cloud Build steps 5a/5b; `make migrate`, `migrate-dry`, `migrate-status`. (AC-001-22)

## Phase 5 — Close

- [ ] **T001-23** Update `docs/20-implementation-status.md` (foundation rows → Built) and `README.md` quick start.
