# Spec 013 — Workspace, Plans & Settings

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (onboarding, free trial, entitlements, plan page, workspace and language settings) · P1 (members, credit-policy overrides) |
| **Owner role** | D: Platform (API, claims, entitlements) + C: Frontend (onboarding, settings) |
| **Depends on** | 001 |
| **Requirements** | FR-060 – FR-068, NFR-07, NFR-11, P0-18, P0-19, P1-11, P1-12 |
| **Design** | [ADR-011](../../adr/ADR-011-workspaces-and-plans-free-trial-only.md), [`contracts/plans.v1.yaml`](../../../contracts/plans.v1.yaml), [`docs/11`](../../11-frontend.md) §6.0, §6.12a, §7a, §10 |

## Summary

A lender signs up, creates a **workspace** in one screen and starts on the **Free trial**. Paid tiers
(Starter, Professional, Enterprise) are shown as **coming soon** and cannot be selected. The backend
enforces the plan's limits wherever an action costs money or a seat. Settings stay narrow: workspace
profile, language (English only, others coming soon), plan and usage; members and four credit-policy
overrides are P1.

## User stories

### US-013-1: Create a workspace on first sign-in

- **AC-013-1** Given a signed-in user without a workspace, `GET /api/me` returns `200` with
  `orgId: null` and `needsWorkspace: true`, the SPA routes to `/onboarding`, and every other `/api`
  route except `GET /api/plans`, `POST /api/workspaces` and `POST /api/invites/{id}/accept` returns
  `403 WORKSPACE_REQUIRED`.
- **AC-013-2** `POST /api/workspaces {name, country: "ID", timezone}` returns `201`. In one Firestore
  transaction it creates `orgs/{orgId}` with `subscription {planId: free_trial, status: TRIALING,
  trialStartedAt: now, trialEndsAt: now + 30 days}`, `defaultLanguage: en`, `currency: IDR`, a member
  doc with role `admin`, and increments `system/signup.workspacesCreated`. Then it sets the custom
  claims `{orgId, role: admin}`. The SPA refreshes the ID token and lands on `/cases`.
- **AC-013-3** A caller who already has a workspace → `409 ALREADY_IN_WORKSPACE`. `SIGNUP_MODE=closed`
  → `403 SIGNUP_CLOSED`; `invite_only` → `403 SIGNUP_CLOSED` unless the caller has a pending invite
  (P1); `system/signup.workspacesCreated ≥ MAX_WORKSPACES` → `403 SIGNUP_CLOSED`.
- **AC-013-4** The bootstrap seeds the demo workspace `org_demo` on the free trial with
  `trialEndsAt = 2026-12-31` and `limitOverrides` (`casesPerMonth 100`, `extractedPagesPerMonth 3000`,
  `runsPerDay 30`, `aiSpendUsdPerMonth "40.00"`), and creates the demo users with their roles.

### US-013-2: Plans and entitlements

- **AC-013-5** `contracts/plans.v1.yaml` is loaded and validated at startup: unknown keys, a missing or
  non-`AVAILABLE` `defaultPlan`, a `COMING_SOON` plan with limits, or invalid override bounds stop the
  process with a clear error.
- **AC-013-6** `GET /api/plans` returns the plans in file order with `status`, `priceLabel` and
  `highlights` (limits only for `AVAILABLE` plans) and the UI languages with their status.
- **AC-013-7** Entitlements are checked by pure functions in `domain/plans.py` at: create case
  (`casesPerMonth`), upload (`fileSizeMb`, `pagesPerDocument`, `documentsPerCase`), start run
  (`runsPerDay`, `aiSpendUsdPerMonth`, and a reservation of the case's uncached, non-blank pages
  against `extractedPagesPerMonth`), invite (`seats`, P1). A violation returns `403 PLAN_LIMIT_REACHED`
  with `limit`, `used` and `max` (upload limits keep their specific codes: `413`, `422`, `409`).
  Effective limits = plan limits overridden by `subscription.limitOverrides`.
- **AC-013-8** After `trialEndsAt`, create case, upload, start run and invite return
  `403 TRIAL_EXPIRED`; reads, finding reviews, suggestion decisions and case decisions keep working;
  `subscription.status` reads `TRIAL_EXPIRED`.
- **AC-013-9** Counters change in the same transaction as the action they meter (case creation →
  `usageMonthly.casesCreated`; run start → `usage.runsStarted` and `usageMonthly.pagesReserved`).
  Two concurrent requests cannot together exceed a limit.
- **AC-013-10** Global guardrails still apply on top of the plan: the effective daily run limit is
  `min(runsPerDay, RUN_QUOTA_PER_ORG_PER_DAY)`; `RUNS_ENABLED=false` → `503 RUNS_DISABLED`.
- **AC-013-11** When a run finishes, its actual usage (`pagesRead`, `pagesCached`, `ocrPages`,
  `parserPages`, `estimatedUsd`) is added to `usageMonthly` and the reservation is replaced by the
  actual pages read; a failed run releases unread reserved pages.

### US-013-3: See my plan and usage

- **AC-013-12** `GET /api/workspace` returns the profile, `subscription` (status, `daysLeft`,
  effective limits) and `usage` (this month's cases, pages and AI spend; today's runs; seats used).
- **AC-013-13** **Settings → Plan & usage** shows the current plan card ("Free trial · 23 days left"),
  usage meters with numbers, and Starter, Professional and Enterprise cards with a **Coming soon**
  badge, their highlights, "Pricing announced later", and a disabled button. Nothing on the page can
  start a purchase.
- **AC-013-14** The app header shows a trial badge. In the last 7 days and after expiry a banner says
  what happens. After expiry, create, upload and run buttons are disabled with the reason in a tooltip.
- **AC-013-15** A `403 PLAN_LIMIT_REACHED` from any action opens a dialog naming the limit, the usage
  and the maximum, with a link to Plan & usage. Upload and run controls warn before the limit
  ("12 of 300 pages left this month"; "This run uses ~28 new pages").

### US-013-4: Workspace settings and language

- **AC-013-16** An admin changes the workspace name and time zone (`PATCH /api/workspace`); others get
  `403 ROLE_REQUIRED`.
- **AC-013-17** **Language & formats** shows English selected and the other languages from
  `plans.v1.yaml` disabled with "Coming soon". `PATCH` with a `coming_soon` language →
  `422 LANGUAGE_NOT_AVAILABLE`. Currency (IDR) and date format are shown read-only.
- **AC-013-18** All onboarding and settings strings come from `locales/en/*.json` (lint rule from
  spec 001); no literal UI strings.

### US-013-5: Members (P1)

- **AC-013-19** An admin invites by email with a role (`POST /api/workspace/invites`; seats checked;
  nothing is emailed). The invitee signs in with that verified email; `GET /api/me` lists the pending
  invite; accepting sets the claims and creates the member doc. Invites expire after 7 days.
- **AC-013-20** An admin removes a member: claims cleared and the member doc removed (the action is
  written to Cloud Logging with actor and target). The last admin cannot be removed or demoted
  (`409 LAST_ADMIN`).

### US-013-6: Credit-policy overrides (P1)

- **AC-013-21** An admin or risk lead sets any of the four overrides within `policyOverrideBounds`
  (`422 VALIDATION_ERROR` outside them, or when `minMonths > requiredMonths`). New runs use the
  effective policy and store `case.policyHash`; existing analyses are unchanged. `GET /api/policy`
  returns effective values with overridden ones marked.

## Out of scope

Payments, checkout, invoices, upgrades and downgrades, proration, emails, SSO, other countries and
currencies, translations into other languages, usage-based billing.

## Edge cases

- Claims are set but the client's token is stale: the SPA forces `getIdToken(true)` and retries
  `GET /api/me` once; if it still says `needsWorkspace`, it shows "Finishing setup…" and retries after
  2 s.
- Month boundaries and the trial end are computed in UTC with the injected `Clock`.
- A run whose pages are all cached reserves 0 pages and passes the page check even at the limit.
- `limitOverrides` can only be set by the server (bootstrap script), never through the API.
