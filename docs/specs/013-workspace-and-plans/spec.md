# Spec 013 — Workspace, Plans, Settings and Roles

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (onboarding for an individual or a company, free trial, entitlements, settings, plan page) · P1 (members and roles) |
| **Owner role** | D: Platform (API, claims, entitlements) + C: Frontend (onboarding, settings) |
| **Depends on** | 001 |
| **Requirements** | FR-003, FR-004, FR-005, FR-071 (P1), NFR-07, NFR-11, P0-01, P0-15, P1-02 |
| **Design** | [ADR-011](../../adr/ADR-011-workspaces-and-plans-free-trial-only.md), [`contracts/plans.v1.yaml`](../../../contracts/plans.v1.yaml), [`docs/10`](../../10-api-contract.md) §5, [`docs/14`](../../14-security-and-compliance.md) §4.2 |

## Summary

A person or a company signs up and creates a **workspace** in one screen: the workspace *is* the
business (or person) whose books are checked. It starts on the **Free trial**; Starter, Professional
and Enterprise are shown as **coming soon**, and so is the **Loan readiness report**. The backend
enforces the plan's limits wherever an action costs money or a seat. In P0 the creator is the only
member (`owner`); P1 adds an accounting team with roles.

## User stories

### US-013-1: Create my workspace

- **AC-013-1** Given a signed-in user without a workspace, `GET /api/me` returns `orgId: null` and
  `needsWorkspace: true`, the SPA routes to `/onboarding`, and every other `/api` route except
  `GET /api/plans`, `POST /api/workspaces` and `POST /api/invites/{id}/accept` returns
  `403 WORKSPACE_REQUIRED`.
- **AC-013-2** Kredibel is for businesses, so onboarding asks no "individual or company" question:
  every workspace is a company. The form has three sections. **Your business:** legal name, trading
  name (optional), legal form, industry, tax ID (optional, stored masked). **Your books:** the
  **currency** (IDR, MYR, SGD, JPY or USD; suggested from the time zone,
  [ADR-020](../../adr/ADR-020-workspace-currency-chosen-at-onboarding.md)), the accounting framework
  (IFRS or US GAAP, a segmented choice) and the time zone. **Main bank account** (optional): bank,
  account number, holder (the legal name unless changed). A request for an individual workspace is
  refused with `422`. `POST
  /api/workspaces` returns `201`; in one transaction it creates `orgs/{orgId}` with `entityType`,
  `profile`, `subscription {planId: free_trial, status: TRIALING, trialEndsAt: now + 30 days}`,
  the chosen `currency`, `defaultLanguage: en`, the member doc with role `owner`, the bank account (mask +
  hash), and increments `system/signup.workspacesCreated`; then it sets the claims `{orgId, role:
  owner}`. The SPA refreshes the token and lands on the dashboard's empty state.
- **AC-013-3** A caller who already has a workspace → `409 ALREADY_IN_WORKSPACE`. `SIGNUP_MODE=closed`
  → `403 SIGNUP_CLOSED`; `invite_only` → `403 SIGNUP_CLOSED` unless the caller has a pending invite;
  `workspacesCreated ≥ MAX_WORKSPACES` → `403 SIGNUP_CLOSED`.
- **AC-013-4** The bootstrap seeds `org_demo` (Sunrise Coffee Roasters, `COMPANY`) on the free trial
  with `trialEndsAt = 2026-12-31` and `limitOverrides` (`documentsPerMonth 600`,
  `extractedPagesPerMonth 3000`, `monthRunsPerDay 200`, `aiSpendUsdPerMonth "40.00"`), and the demo
  owner.

### US-013-2: Plans and entitlements

- **AC-013-5** `contracts/plans.v1.yaml` is loaded and validated at startup: unknown keys, a missing or
  non-`AVAILABLE` `defaultPlan`, or a `COMING_SOON` plan with limits stop the process.
- **AC-013-6** `GET /api/plans` returns plans in file order, `comingSoonFeatures` and the UI languages.
- **AC-013-7** Pure checks in `domain/plans.py` run at: upload (`fileSizeMb`, `pagesPerDocument`,
  `ledgerRowsPerFile`, `documentsPerMonth`, page reservation against `extractedPagesPerMonth`, AI
  spend), month run (`monthRunsPerDay`), assistant question (`assistantQuestionsPerDay`), invite
  (`seats`). A violation returns `403 PLAN_LIMIT_REACHED` with `limit`, `used`, `max` (upload size and
  shape keep `413`/`422`; a user's month run over `monthRunsPerDay` or `RUN_QUOTA_PER_ORG_PER_DAY`
  is `429 RUN_QUOTA_EXCEEDED` with `retryAfterSeconds`, as in [`docs/10`](../../10-api-contract.md) §3
  and AC-004-11). Exact duplicates never count.
- **AC-013-8** After `trialEndsAt`, upload, re-run, assistant and invite return `403 TRIAL_EXPIRED`;
  reading the books, resolving review items and dismissing findings keep working.
- **AC-013-9** Counters change in the same transaction as the action they meter; two concurrent
  uploads at the limit cannot both pass.
- **AC-013-10** When a document run finishes, actual pages read, cached and OCR'd and the estimated
  spend replace the reservation in `usageMonthly`.

### US-013-3: Plan, usage and coming soon

- **AC-013-11** **Settings → Plan & usage** shows "Free trial · 23 days left", usage meters (documents,
  pages, AI spend, month runs today, seats), Starter, Professional and Enterprise with a **Coming soon**
  badge and disabled buttons, and the **Loan readiness report** and **Bank feeds** as coming-soon
  features. Nothing can start a purchase.
- **AC-013-12** The trial status is always visible: from 1200 px as a compact row at the sidebar foot (days
  left and pages read this month with progress meter, fitting within 768 px viewport height without
  scrolling, opening Plan and usage), below that as a badge in the top bar; in the last 7 days and after
  expiry a banner says what happens; after expiry Upload is disabled with the reason.
- **AC-013-13** A `403 PLAN_LIMIT_REACHED` opens a dialog naming the limit, the usage and the maximum;
  the upload sheet warns before ("4 of 400 pages left this month").

### US-013-4: Settings

- **AC-013-14** **Profile**: names, trading name, legal form (company), industry, tax ID (stored
  masked), address, aliases; the entity type and reporting currency are shown and fixed (with "Coming soon"
  for changing currency). **Bank accounts**: list (masked), add, nickname, ledger account code, delete when
  no statement uses it.
- **AC-013-15** **Language & formats**: English selected; other languages disabled with "Coming soon"
  (`422 LANGUAGE_NOT_AVAILABLE` on PATCH); the currency is shown read-only with "Coming soon" for
  changing it (it is not part of the PATCH body), and the date format is read-only.
- **AC-013-16** All strings come from `locales/en/*.json`.

### US-013-5: An accounting team (P1)

- **AC-013-17** The owner invites by email with a role (`accountant`, `reviewer`, `viewer`; seats
  checked; nothing is emailed; the invite link is shown to copy). The invitee signs in with that
  verified email and accepts; claims are set by the server. Invites expire after 7 days.
- **AC-013-18** Every endpoint enforces the matrix of [`docs/10`](../../10-api-contract.md) §5 through
  `domain/access.py` (`403 ROLE_REQUIRED` with `requiredRoles`); the UI hides or disables actions the
  role cannot take and says why ("A reviewer confirms duplicates").
- **AC-013-19** The owner removes a member or changes a role; the last owner cannot be removed or
  demoted (`409 LAST_OWNER`).

## Out of scope

Payments, checkout, upgrades, emails, SSO, several workspaces per user, other countries and
translations, changing a workspace's currency after onboarding and converting between currencies
(ADR-020), the loan readiness report itself.

## Edge cases

- Claims set but the token is stale: the SPA forces `getIdToken(true)` and retries `GET /api/me` once;
  if still `needsWorkspace`, it shows "Finishing setup…" and retries after 2 s.
- Month boundaries and the trial end use the injected `Clock`; usage months are UTC, book months are
  in the workspace's time zone.
- `limitOverrides` can only be set by the server (bootstrap script), never through the API.
- A workspace's currency can only be changed by support with `scripts/set_workspace_currency.py`,
  which refuses when the workspace already has documents unless `--force` (ADR-020).
- A claim (or a `system/signup/users/{uid}` record) that names a workspace which does not exist, because
  it was never created or a demo reset removed it, counts as no workspace: `GET /api/me` answers
  `needsWorkspace: true`, onboarding runs, and creating the workspace replaces the stale claim.
