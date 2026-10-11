# Tasks 013 — Workspace, Plans, Settings and Roles

Phases 1–3 are needed by specs 003 and 004 (D1). Phase 4 can follow on D5–D6. Phase 5 is P1.

## Phase 1 — Plans in the domain (TDD)

- [x] **T013-01** **TDD** `load_plans`: valid file loads; unknown key, missing default plan, `COMING_SOON` plan with limits → error. (AC-013-5)
- [ ] **T013-02** **TDD** `effective_limits` with `limitOverrides`; `subscription_status` before and after `trialEndsAt` (injected clock). (AC-013-4, AC-013-8)
- [ ] **T013-03** **TDD** `check_upload` (each limit, exact duplicates free, all-cached = 0 pages), `check_month_run`, `check_assistant_question`, `check_invite`; `Denied` carries `limit`, `used`, `max`. (AC-013-7)

## Phase 2 — Workspace API

- [ ] **T013-04** **TDD** `core/auth.py`: optional `org_id`, `require_workspace` → `403 WORKSPACE_REQUIRED`; `GET /api/me` with and without a workspace. (AC-013-1)
- [ ] **T013-05** `IdentityAdmin` port, Firebase adapter, fake.
- [ ] **T013-06** **TDD** `WorkspaceService.create` for `INDIVIDUAL` and `COMPANY`: transaction (org, profile, subscription, owner member, bank account mask + hash, signup counter), claims after commit, `ALREADY_IN_WORKSPACE`, `SIGNUP_CLOSED` per mode and `MAX_WORKSPACES`. (AC-013-2, AC-013-3)
- [ ] **T013-07** **TDD** `EntitlementService` with counters in the same transaction; concurrency at the limit; usage settlement at run end. (AC-013-7, AC-013-9, AC-013-10)
- [ ] **T013-08** Plans, workspace and bank-account routes; `LANGUAGE_NOT_AVAILABLE`. (AC-013-6, AC-013-14, AC-013-15)
- [ ] **T013-09** `scripts/seed_demo_workspace.py`; call it from `infra/bootstrap.sh`. (AC-013-4)

## Phase 3 — Wiring (with 003 and 004)

- [ ] **T013-10** Call `EntitlementService` from `DocumentService.upload`, `runs.start_month_run` (user re-runs) and the assistant; integration tests for every `403`/`413`/`422` code. (AC-013-7, AC-013-8)

## Phase 4 — Frontend

- [ ] **T013-11** `OnboardingPage` with the individual-or-company choice; router guard; forced token refresh and one retry. (AC-013-1, AC-013-2)
- [ ] **T013-12** Trial badge and banner; Upload disabled after expiry. (AC-013-12)
- [ ] **T013-13** Settings: Profile, Bank accounts, Language & formats. (AC-013-14…16)
- [ ] **T013-14** Plan & usage with coming-soon plans and features. (AC-013-11)
- [ ] **T013-15** `PlanLimitDialog` and early warnings in the upload sheet. (AC-013-13)

## Phase 5 — P1 roles

- [ ] **T013-16** **TDD** `domain/access.py` table test: every endpoint × role. (AC-013-18)
- [ ] **T013-17** Members and invites (API + Members section); last-owner rule; role-aware UI. (AC-013-17…19)

## Phase 6 — Verify

- [ ] **T013-18** On the deployed env: a new Google account → onboarding as a company → free trial → Plan & usage shows limits and coming-soon items; `SIGNUP_MODE=closed` blocks a second new account.
- [ ] **T013-19** Update `docs/20-implementation-status.md`.
