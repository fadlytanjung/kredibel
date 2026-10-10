# Plan 013 — Workspace, Plans & Settings

## Approach

Plans are data, entitlement checks are pure functions, and every counter moves inside the same
Firestore transaction as the action it meters. The workspace is the existing `org`; this spec adds
self-serve creation, a subscription block and a small settings area. Phase 1–3 land on D1 so specs
003 and 004 can call the entitlement service from the start; the settings UI can follow later.

## Backend

| File | Content |
|---|---|
| `contracts/plans.v1.yaml` | Plan catalog, limits, features, languages, policy override bounds |
| `domain/plans.py` | Pydantic models `PlanCatalog`, `Plan`, `Limits`; `load_plans(path)` with validation; `effective_limits(plan, overrides)`; `check_create_case`, `check_upload`, `check_start_run`, `check_invite` → `Allowed` or `Denied(code, limit, used, max)`; `subscription_status(sub, now)` |
| `domain/models/workspace.py` | `Workspace`, `Subscription`, `UsageMonth`, `UsageDay`, `PolicyOverrides` |
| `ports/identity_admin.py` | `IdentityAdmin`: `set_claims(uid, claims)`, `get_user(uid) -> {email, emailVerified}` |
| `adapters/firebase_identity.py` | Firebase Admin SDK implementation; fake in `tests/fakes/` |
| `ports/repository.py` | `WorkspaceRepository`: `create_workspace_txn`, `get_workspace`, `update_workspace`, `get_usage`, `increment_in_txn(...)`, members and invites (P1) |
| `adapters/firestore_repo.py` | implementation; `system/signup` counter |
| `services/workspace_service.py` | create (signup mode, max workspaces, already-in-workspace), get with usage and days left, update (role checks, language availability), members/invites (P1), policy overrides (P1) |
| `services/entitlement_service.py` | loads subscription + usage, calls `domain/plans.py`, raises `PlanLimitReached` / `TrialExpired`; offers `reserve_pages(case)` used by `AnalysisService` |
| `core/auth.py` | `Principal.org_id: str | None`; dependency `require_workspace` (→ `403 WORKSPACE_REQUIRED`); `require_role(...)` |
| `core/errors.py` | `WORKSPACE_REQUIRED`, `SIGNUP_CLOSED`, `ALREADY_IN_WORKSPACE`, `TRIAL_EXPIRED`, `PLAN_LIMIT_REACHED`, `LANGUAGE_NOT_AVAILABLE`, `LAST_ADMIN` |
| `api/me.py`, `api/plans.py`, `api/workspace.py` | routes per `contracts/openapi.yaml` |
| `scripts/seed_demo_workspace.py` | creates `org_demo` with overrides and demo users (replaces the org part of `set_claims.py`) |
| Settings | `SIGNUP_MODE` (`open`), `MAX_WORKSPACES` (15), `PLANS_FILE` (`contracts/plans.v1.yaml`) |

## Frontend

| File | Content |
|---|---|
| `pages/OnboardingPage.tsx` + `features/create-workspace/` | one-screen form; token refresh; redirect logic in the router (`needsWorkspace`) |
| `widgets/AppHeader/` | workspace name, trial badge, user menu |
| `widgets/TrialBanner/` | last 7 days and expired states |
| `pages/SettingsPage.tsx` | left rail: Workspace, Language & formats, Plan & usage, Credit policy (P1), Members (P1) |
| `widgets/PlanAndUsage/` | `PlanCard` (current / coming soon), `UsageMeter` |
| `features/plan-limit-dialog/` | maps `PLAN_LIMIT_REACHED` and `TRIAL_EXPIRED` to a dialog |
| `entities/workspace/`, `entities/plan/` | query hooks, mappers |
| `shared/ui/ComingSoonBadge.tsx` | badge + disabled wrapper with tooltip |
| `shared/i18n/locales/en/settings.json`, `onboarding.json` | strings |

## Constitution check

P1 ✔ · P4 ✔ (limits enforced server-side; claims set by the server only) · P5 n/a · P7 ✔ (Firebase
Auth, Firestore) · P8 ✔ · P9 ✔ (P1 parts flagged) · P10 ✔ (pure entitlement functions unit-tested)

## Risks

- Custom claims need the web service account to hold `roles/firebaseauth.admin` (docs/16 §4).
- Token refresh timing after claims → handled by the forced refresh + one retry (spec edge case).
- Public sign-up during judging is an abuse surface → `SIGNUP_MODE`, `MAX_WORKSPACES`, small trial
  limits, AI-spend cap, budget alerts (docs/14 §2, docs/21 §5).
