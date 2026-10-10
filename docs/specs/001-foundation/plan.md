# Plan 001 — Foundation

## Approach

Build the composition root and the seams first, so later specs only add modules. One image, role
selected by `APP_ROLE`. Same-origin SPA served by FastAPI in the cloud and proxied by Vite locally.

## Backend

| File | Content |
|---|---|
| `backend/pyproject.toml` | Python 3.12; deps: fastapi, uvicorn[standard], pydantic, pydantic-settings, structlog, firebase-admin, google-cloud-firestore, google-cloud-storage, google-cloud-tasks, google-cloud-documentai, google-cloud-modelarmor, google-genai, google-adk (2.11.x), pikepdf, pdfplumber, pypdfium2, rapidfuzz, python-ulid, anyio, opentelemetry (FastAPI + GCP exporter via `google-adk[otel-gcp]`); dev: pytest, pytest-asyncio, hypothesis, httpx, ruff, pyright, import-linter |
| `backend/app/core/settings.py` | `Settings(BaseSettings)` with every variable of [`docs/16`](../../16-infrastructure-and-deployment.md) §6.1; `APP_ROLE: Literal["web","worker","all"]` |
| `backend/app/core/logging.py` | structlog JSON config; request middleware binding `request_id`, trace header → `logging.googleapis.com/trace` |
| `backend/app/core/errors.py` | `DomainError(code, status, title)` hierarchy; problem+json exception handlers (incl. validation) |
| `backend/app/core/auth.py` | `Principal`; `verify_request(authorization) -> Principal` using `firebase_admin.auth.verify_id_token`; FastAPI dependency `current_principal` |
| `backend/app/core/security_headers.py` | middleware adding CSP & co. |
| `backend/app/core/clock.py`, `ids.py` | `Clock` protocol + `SystemClock`; ULID helpers with prefixes; `case_reference()` |
| `backend/app/api/health.py`, `api/me.py` | routes |
| `backend/app/api/static.py` | serve `/app/static` with SPA fallback (web/all only) |
| `backend/app/main.py` | `create_app(settings, deps=None)`; mounts routers by role; `app = create_app(Settings())` |
| `backend/.importlinter` | layer contracts of [`docs/13`](../../13-design-patterns-and-conventions.md) §2.1 |
| `backend/scripts/set_claims.py` | set `{orgId, role}` claims + upsert `orgs/{orgId}/members/{uid}` |
| `backend/tests/integration/test_auth.py` | 401/403/200 cases with a fake verifier |

## Frontend

| File | Content |
|---|---|
| `frontend/` | Vite React-TS app; Tailwind v4; tokens from [`docs/12`](../../12-design-system.md) §2 |
| `src/shared/firebase/app.ts` | init from `VITE_FIREBASE_*` |
| `src/shared/api/client.ts` | typed fetch with ID token, problem parsing, 401 handling |
| `src/shared/ui/*` | Button, Card, Badge, EmptyState, Skeleton, Toast (first batch) |
| `src/app/providers/AuthProvider.tsx` | auth state, `useMe()` |
| `src/pages/LoginPage.tsx`, `CaseListPage.tsx` (empty state), `OnboardingPage.tsx` (placeholder until 013), `NotFoundPage.tsx` | |
| `src/shared/i18n/` | `setup.ts` (i18next, `en` only), `languages.ts`, `locales/en/common.json`; ESLint `i18next/no-literal-string` |
| `src/app/router.tsx` | protected routes |

## Infra & tooling

`Dockerfile` (multi-stage), `cloudbuild.yaml`, `infra/bootstrap.sh`, `infra/firebase.json`
(rules/indexes from `contracts/`), `infra/env.web.yaml`, `infra/env.worker.yaml`, `Makefile`,
`tools/checks/no_long_prompts.py`, `tools/checks/scan_secrets.py`, `.gitignore`, `.pre-commit-config.yaml`.

## Constitution check

P1 ✔ (spec exists) · P2 n/a · P3 n/a · P4 ✔ (auth server-side) · P5 n/a · P6 n/a · P7 ✔ (Firebase,
Cloud Run, Cloud Build) · P8 ✔ (no data) · P9 ✔ (skeleton deployed day 1) · P10 ✔ (gates)

## Risks

- ADK/OTel extras version conflicts → pin and use the constraints file recommended on PyPI.
- Firebase authorized domains must include the Cloud Run URL before Google sign-in works.
