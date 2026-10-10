# Tasks 013 — Workspace, Plans & Settings

Phases 1–3 are needed by specs 003 and 004 (D1). Phase 4 can follow on D5–D6. Phase 5 is P1.

## Phase 1 — Plans in the domain (TDD)

- [ ] **T013-01** **TDD** `load_plans`: valid file loads; unknown key, missing default plan, `COMING_SOON` plan with limits, bad bounds → error. (AC-013-5)
- [ ] **T013-02** **TDD** `effective_limits` with `limitOverrides`; `subscription_status` before/after `trialEndsAt` (injected clock). (AC-013-4, AC-013-8)
- [ ] **T013-03** **TDD** `check_create_case`, `check_upload`, `check_start_run` (runs/day with `min(plan, env)`, AI spend, page reservation incl. all-cached = 0), `check_invite`; `Denied` carries `limit`, `used`, `max`. (AC-013-7, AC-013-10)

## Phase 2 — Workspace API

- [ ] **T013-04** **TDD** `core/auth.py`: optional `org_id`, `require_workspace` → `403 WORKSPACE_REQUIRED`; `GET /api/me` with and without a workspace. (AC-013-1)
- [ ] **T013-05** `IdentityAdmin` port, Firebase adapter, fake.
- [ ] **T013-06** **TDD** `WorkspaceService.create`: transaction (org, subscription, member admin, signup counter), claims set after commit, `ALREADY_IN_WORKSPACE`, `SIGNUP_CLOSED` for each mode and for `MAX_WORKSPACES`. (AC-013-2, AC-013-3)
- [ ] **T013-07** **TDD** `EntitlementService` + counters in the same transaction; concurrency test (two parallel case creations at the limit → one succeeds). (AC-013-7, AC-013-9)
- [ ] **T013-08** `api/plans.py`, `api/workspace.py` (GET; PATCH name, time zone, language with `LANGUAGE_NOT_AVAILABLE`). (AC-013-6, AC-013-12, AC-013-16, AC-013-17)
- [ ] **T013-09** `scripts/seed_demo_workspace.py`; call it from `infra/bootstrap.sh`. (AC-013-4)

## Phase 3 — Wiring (with 003 and 004)

- [ ] **T013-10** Call `EntitlementService` from `CaseService.create`, `DocumentService.upload`, `AnalysisService.start_run` (page reservation) and finalize usage at run end; integration tests for every `403`/`413`/`422`/`409` code. (AC-013-7, AC-013-8, AC-013-11)

## Phase 4 — Frontend

- [ ] **T013-11** `OnboardingPage` + `create-workspace` feature; router guard on `needsWorkspace`; forced token refresh and one retry. (AC-013-1, AC-013-2)
- [ ] **T013-12** `AppHeader` trial badge + `TrialBanner`; disabled create/upload/run after expiry. (AC-013-14)
- [ ] **T013-13** Settings shell; Workspace and Language & formats sections (English selected, others "Coming soon"). (AC-013-16, AC-013-17, AC-013-18)
- [ ] **T013-14** Plan & usage: current plan card, usage meters, three coming-soon cards with disabled buttons. (AC-013-13)
- [ ] **T013-15** `PlanLimitDialog` + early warnings in the dropzone and on Run analysis. (AC-013-15)

## Phase 5 — P1

- [ ] **T013-16** Members and invites (API + Members section); last-admin rule. (AC-013-19, AC-013-20)
- [ ] **T013-17** **TDD** credit-policy overrides: bounds, `minMonths ≤ requiredMonths`, effective policy, `policyHash`; Credit policy section; `GET /api/policy` marks overrides. (AC-013-21)

## Phase 6 — Verify

- [ ] **T013-18** On the deployed env: a new Google account signs in → onboarding → free trial → Plan & usage shows limits and coming-soon tiers; `SIGNUP_MODE=closed` blocks a second new account.
- [ ] **T013-19** Update `docs/20-implementation-status.md`.
