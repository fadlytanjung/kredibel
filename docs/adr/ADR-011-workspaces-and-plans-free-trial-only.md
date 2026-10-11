# ADR-011 — Workspaces and plans: free trial only, no billing

**Status:** Accepted · **Date:** 2026-10-10

## Context

The product needs a commercial shape: a business (or a person) signs up as a **workspace**, starts on a plan, and sees
what paid tiers will offer. For the competition we must not take payments, must stay within a small
cloud budget ([`21`](../21-cost-analysis.md)), and must keep the build small. Every AI-heavy action
(upload, reading, month runs, assistant questions) costs money, so limits need to be enforced on the server, not only
shown in the UI.

## Decision

- **Workspace = organization** (`orgs/{orgId}`). A signed-in user without a workspace creates one in a
  one-screen onboarding (individual or company, name, time zone). The creator becomes `owner`. The server sets the
  Firebase custom claims; the client refreshes its ID token.
- **Plans are configuration**, in [`contracts/plans.v1.yaml`](../../contracts/plans.v1.yaml). One plan
  is `AVAILABLE`: **Free trial** (30 days). `Starter`, `Professional` and `Enterprise` are listed as
  `COMING_SOON`: visible, disabled, no prices, no checkout.
- **Entitlements are checked in the backend** (`domain/plans.py`, pure) at the points that cost money
  or seats: upload (documents, pages, size, rows, AI spend), month re-run, assistant question, invite
  member. Errors are `403 PLAN_LIMIT_REACHED` (with
  the limit, usage and maximum) and `403 TRIAL_EXPIRED`.
- **After the trial:** no new uploads, re-runs or assistant questions, but the books stay readable and
  review items and findings can still be resolved.
- **Global guardrails stay above plans:** `RUNS_ENABLED`, `RUN_QUOTA_PER_ORG_PER_DAY`, `SIGNUP_MODE`
  and `MAX_WORKSPACES` (env) cap the whole deployment regardless of plan.
- **Workspace settings stay narrow:** profile, bank accounts, language (English only), plan and usage,
  members and roles (P1). The loan readiness report and bank feeds are listed as coming-soon features.

## Alternatives considered

| Option | Why not |
|---|---|
| Billing integration now | Payments are out of scope; no third-party SaaS (P7) |
| Hard-code limits in code | Limits change per plan and per demo; config is reviewable and testable |
| Limits only in the UI | Anyone with a token could still run up the bill |
| No self-serve sign-up (seeded demo org only) | Judges and pilot businesses could not try it; the trial would be fiction |

## Consequences

- One new config file with a schema check at startup, one pure module, one service, and five call
  sites. Usage counters live in `orgs/{orgId}/usage/*` (already used for run quotas).
- Paid tiers can later map to Google Cloud Marketplace or a billing provider without changing the
  entitlement checks.
- Self-serve sign-up is an abuse surface: `SIGNUP_MODE` (`open`, `invite_only`, `closed`),
  `MAX_WORKSPACES`, small trial limits and budget alerts bound the worst case
  ([`14`](../14-security-and-compliance.md) §2, [`21`](../21-cost-analysis.md) §5).
