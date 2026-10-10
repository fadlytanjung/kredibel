# Spec 001 — Foundation

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | D: Platform (with C for the frontend shell) |
| **Depends on** | — |
| **Requirements** | FR-001, FR-002, NFR-06, NFR-10, NFR-11, P0-01, P0-17 |

## Summary

A walking skeleton: repository layout, backend and frontend shells, Firebase sign-in, org/role
claims, quality gates, container image, and deployment of `kredibel-web` and `kredibel-worker` to
Cloud Run. Nothing domain-specific yet. Everything later builds on these seams.

## User stories

### US-001-1: Run locally with one command (developer)

- **AC-001-1** Given a fresh clone with `gcloud` ADC configured, when I run `make setup && make dev`,
  then the API answers `GET /api/health` with `{"status":"ok","version":…,"role":"all"}` and the SPA
  shows the login page at `http://localhost:5173`.
- **AC-001-2** Given `make dev` is running, when the SPA calls `/api/*`, then Vite proxies to the
  backend (no CORS configuration exists).

### US-001-2: Sign in and see my workspace (analyst)

- **AC-001-3** Given a Firebase user with claims `{orgId: "org_demo", role: "analyst"}`, when they
  sign in with email/password or Google, then they land on `/cases` and see an empty state.
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

## Non-functional

- Responses include the security headers of [`docs/14`](../../14-security-and-compliance.md) §8.
- Logs are JSON with `service`, `version`, and the trace field.

## Out of scope

Cases, documents, any Google AI service, member management UI.

## Edge cases

- Token from a different Firebase project → 401.
- Clock skew on token `iat` → accepted within the Admin SDK's default tolerance.
