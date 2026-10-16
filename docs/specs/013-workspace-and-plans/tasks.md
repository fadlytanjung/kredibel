# Tasks 013 — Workspace, Plans, Settings and Roles

Phases 1–3 are needed by specs 003 and 004 (D1). Phase 4 can follow on D5–D6. Phase 5 is P1.

## Phase 1 — Plans in the domain (TDD)

- [x] **T013-01** **TDD** `load_plans`: valid file loads; unknown key, missing default plan, `COMING_SOON` plan with limits → error. (AC-013-5)
- [x] **T013-02** **TDD** `effective_limits` with `limitOverrides`; `subscription_status` before and after `trialEndsAt` (injected clock). (AC-013-4, AC-013-8)
- [x] **T013-03** **TDD** `check_upload` (each limit, exact duplicates free, all-cached = 0 pages), `check_month_run`, `check_assistant_question`, `check_invite`; `Denied` carries `limit`, `used`, `max`. (AC-013-7)

## Phase 2 — Workspace API

- [x] **T013-04** **TDD** `core/auth.py`: optional `org_id`, `require_workspace` → `403 WORKSPACE_REQUIRED`; `GET /api/me` with and without a workspace. (AC-013-1)
- [x] **T013-05** `IdentityAdmin` port, Firebase adapter, fake.
- [x] **T013-06** **TDD** `WorkspaceService.create` for `INDIVIDUAL` and `COMPANY`: transaction (org, profile, subscription, owner member, bank account mask + hash, signup counter), claims after commit, `ALREADY_IN_WORKSPACE`, `SIGNUP_CLOSED` per mode and `MAX_WORKSPACES`. (AC-013-2, AC-013-3) `MAX_WORKSPACES` raised from 15 to 200 on 16 Oct 2026 (commit eb478ae, which cites T013-03 by mistake).
- [x] **T013-07** **TDD** `EntitlementService` with counters in the same transaction; concurrency at the limit; usage settlement at run end. (AC-013-7, AC-013-9, AC-013-10)
- [x] **T013-08** Plans, workspace and bank-account routes; `LANGUAGE_NOT_AVAILABLE`. (AC-013-6, AC-013-14, AC-013-15)
- [x] **T013-09** `scripts/seed_demo_workspace.py`; call it from `infra/bootstrap.sh`. (AC-013-4)

## Phase 3 — Wiring (with 003 and 004)

- [x] **T013-10** Call `EntitlementService` from `DocumentService.upload`, `runs.start_month_run` (user re-runs) and the assistant; integration tests for every `403`/`413`/`422` code. (AC-013-7, AC-013-8) Upload and user month runs done; the assistant's check lands with T011-04.

## Phase 4 — Frontend

- [x] **T013-11** `OnboardingPage`; router guard; forced token refresh and one retry. (AC-013-1, AC-013-2)
- [x] **T013-11a** Onboarding for businesses only: no individual-or-company choice; three sections (your
  business with legal form and tax ID, your books with a segmented IFRS / US GAAP framework, an optional
  main bank account whose holder starts as the legal name); `POST /api/workspaces` creates a company and
  refuses an individual with 422. (AC-013-2)
- [x] **T013-12** Trial badge and banner; Upload disabled after expiry. (AC-013-12)
- [x] **T013-13** Settings: Profile, Bank accounts, Language & formats. (AC-013-14…16)
- [x] **T013-13a** Settings → Bank accounts is a `DataTable`: chips declared or detected with counts, search
  by nickname, bank, masked number, holder or ledger code, 10 a page; edit and remove stay in the row.
  (AC-013-14)
- [x] **T013-14** Plan & usage with coming-soon plans and features. (AC-013-11)
- [x] **T013-15** `PlanLimitDialog` and early warnings in the upload sheet. (AC-013-13)
- [x] **T013-20** **TDD** The workspace currency ([ADR-020](../../adr/ADR-020-workspace-currency-chosen-at-onboarding.md)): chosen at onboarding with a suggestion from the time zone; not in the PATCH body; read-only with "Coming soon" in Settings; `scripts/set_workspace_currency.py` for support (refuses with documents unless `--force`, audited); `formatMoney` decimals per currency. (AC-013-2, AC-013-15)

## Phase 5 — P1 roles

- [ ] **T013-16** **TDD** `domain/access.py` table test: every endpoint × role. (AC-013-18)
- [ ] **T013-17** Members and invites (API + Members section); last-owner rule; role-aware UI. (AC-013-17…19)

## Phase 6 — Verify

- [ ] **T013-18** On the deployed env: a new Google account → onboarding as a company → free trial → Plan & usage shows limits and coming-soon items; `SIGNUP_MODE=closed` blocks a second new account.
- [x] **T013-19** Update `docs/20-implementation-status.md`.
