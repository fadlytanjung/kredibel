# Spec 001 — Foundation

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | D: Platform (with C for the frontend shell) |
| **Depends on** | — |
| **Requirements** | FR-001, FR-002, NFR-06, NFR-10, NFR-11, NFR-13, NFR-14, NFR-15, P0-01, P0-17 |
| **Design** | [`docs/12`](../../12-design-system.md) §0, §5; [`docs/22`](../../22-data-migrations.md); [ADR-013](../../adr/ADR-013-versioned-documents-and-forward-migrations.md) |

## Summary

A walking skeleton: repository layout, backend and frontend shells, Firebase sign-in, org/role
claims, quality gates, container image, and deployment of `kredibel-web` and `kredibel-worker` to
Cloud Run. It also lays the two seams that keep later work cheap to change: the **design foundation**
(generated tokens, the responsive app shell, Storybook and visual tests) and the **data-migration
foundation** (versioned documents, upcasters, the migration runner and job, backups). Nothing
domain-specific yet. Everything later builds on these seams.

## User stories

### US-001-1: Run locally with one command (developer)

- **AC-001-1** Given a fresh clone with `gcloud` ADC configured, when I run `make setup && make dev`,
  then the API answers `GET /api/health` with `{"status":"ok","version":…,"role":"all"}` and the SPA
  shows the login page at `http://localhost:5173`.
- **AC-001-2** Given `make dev` is running, when the SPA calls `/api/*`, then Vite proxies to the
  backend (no CORS configuration exists).

### US-001-2: Sign in and see my workspace (owner)

- **AC-001-3** Given a Firebase user with claims `{orgId: "org_demo", role: "owner"}`, when they
  sign in with email/password or Google, then they land on the dashboard (`/`) and see its empty
  state ("Upload your first documents").
- **AC-001-4** Given a signed-in user **without** an `orgId` claim, when the SPA calls `GET /api/me`,
  then the API returns `200` with `orgId: null` and `needsWorkspace: true`, other routes return
  `403 WORKSPACE_REQUIRED`, and the SPA shows the `/onboarding` placeholder (the form arrives with
  spec 013).
- **AC-001-5** Given no or an invalid/expired token, when any `/api` route except `/api/health` is
  called, then the API returns `401 UNAUTHENTICATED` as `application/problem+json`.
- **AC-001-6** `GET /api/me` returns `uid`, `email`, `displayName`, `orgId`, `role` from the verified
  token, plus `needsWorkspace` and `language: "en"`.
- **AC-001-7** Sign-out clears the session and returns to `/login`.

### US-001-3: Deploy (team)

- **AC-001-8** Given the bootstrap has run, when `make deploy` runs, then Cloud Build runs checks,
  builds one image, deploys `kredibel-worker` (IAM-only) and `kredibel-web` (public), and the smoke step
  confirms `/api/health` reports the new version.
- **AC-001-9** An unauthenticated request to `kredibel-worker` is rejected by Cloud Run (`403`).
- **AC-001-10** `kredibel-web` does not mount `/tasks/*`; `kredibel-worker` does not mount `/api/*`
  routes except `/api/health`.

### US-001-4: Quality gates (team)

- **AC-001-11** `make check` runs ruff, pyright, import-linter, repo checks, pytest, eslint, tsc and
  vitest, and fails if any fails.
- **AC-001-12** A Python string literal longer than 200 characters under `backend/app/agents/`
  (outside `prompts/`) fails `make check`.
- **AC-001-13** Importing `adapters` from `domain` fails `make check` (import-linter).

### US-001-5: Built for more languages, English only (team)

- **AC-001-14** The SPA initializes i18next with the `en` resources from
  `src/shared/i18n/locales/en/*.json`; components read strings with `useTranslation()`; the ESLint
  rule `i18next/no-literal-string` fails `make check` on a hard-coded UI string; `formatMoney` and
  `formatDate` use `Intl` with the active locale.

### US-001-6: Design foundation (team)

- **AC-001-15** `make tokens` generates `frontend/src/app/styles/tokens.css` and
  `tailwind-theme.css` from `contracts/design/tokens.json`; `make tokens-check` fails when a generated
  file is stale or a listed contrast pair is below its minimum.
- **AC-001-16** The app shell shows the navigation of [`docs/11`](../../11-frontend.md) §4 (Dashboard,
  Documents, Reconciliation, Review, Risk, Clients & suppliers, Assistant (P1)) as a
  labelled sidebar from 1200 px, a rail with short labels from 600 to 1199 px, and below 600 px a
  bottom navigation (Dashboard, Documents, Review, Risk, More) with the rest in the More sheet;
  Settings opens from the profile row (avatar, name, role) at the foot of the sidebar and rail, and
  from the More sheet; the labelled sidebar fits a window 768 px tall without scrolling; the logo,
  the workspace name, the trial status and a global **Upload** action are always reachable; no
  horizontal page scroll at 360 px.
- **AC-001-17** Storybook builds with the first `shared/ui` components (Button, Badge, Panel,
  EmptyState, Skeleton, Toast, AppShell); every story passes axe; Playwright visual tests of the
  shell and the login page at 390, 834 and 1440 px pass against committed baselines.
- **AC-001-18** `tools/checks/no_raw_styles.py` fails `make check` on a raw colour (`#…`, `rgb(`,
  `hsl(`), an arbitrary Tailwind value (`[#…]`, `[13px]`) or a `style=` prop outside the allow-list.

### US-001-7: Data-migration foundation (team)

- **AC-001-19** Every persistence model declares `SCHEMA_VERSION`; repositories upcast on read and
  write the latest version; a stored v1 fixture of the `documents` sample model reads as the latest
  version.
- **AC-001-20** Against the emulator, `python -m migrations run` applies the sample migration
  `0000_example`, records `system/migrations/0000_example` as `DONE` with counts, skips it on a
  second run, resumes from its checkpoint after being killed half-way, and refuses to start while
  another runner holds `system/migrationLock`.
- **AC-001-21** Changing a persistence model without updating `contracts/data/schema-snapshot.json`
  fails `make check` (`tools/checks/schema_drift.py`).
- **AC-001-22** The `kredibel-migrate` Cloud Run job is deployed by Cloud Build after the index and
  rules deploy and before the services; point-in-time recovery and the daily backup schedule are on
  for `(default)` (`gcloud firestore databases describe` shows PITR enabled).

## Non-functional

- Responses include the security headers of [`docs/14`](../../14-security-and-compliance.md) §8.
- Logs are JSON with `service`, `version`, and the trace field.

## Out of scope

Documents, months, any Google AI service, member management UI.

## Edge cases

- Token from a different Firebase project → 401.
- Clock skew on token `iat` → accepted within the Admin SDK's default tolerance.
