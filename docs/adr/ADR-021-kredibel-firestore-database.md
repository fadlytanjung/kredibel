# ADR-021 — Kredibel's own Firestore database in the shared project

**Status:** Accepted · **Date:** 2026-10-12 · **Supersedes:** "the `(default)` database only" in
[`16`](../16-infrastructure-and-deployment.md) §7 and [`21`](../21-cost-analysis.md)

## Context

`cloud-hack2skill` hosts several apps. The others already keep their data in named databases
(`coffee-menu`, `reflect-ai-app`); `(default)` held Kredibel's data next to composite indexes and a
rules release left there by another project. Kredibel's indexes had never been deployed, so the
document list failed with "the query requires an index", and a rules deploy to `(default)` was one
command away from replacing a ruleset another app's history shares.

## Decision

- Kredibel uses its own database, **`kredibel`** (Native, `asia-southeast1`, point-in-time recovery,
  delete protection, daily backup with 7-day retention).
- Every client names it: `FIRESTORE_DATABASE=kredibel` for the services, the migrate job, scripts and
  local development (`make dev-backend`); `VITE_FIRESTORE_DATABASE=kredibel` for the SPA's listeners.
  The setting defaults to `(default)`, which the emulator and the tests use.
- `firebase.json` (one config, at the repository root) targets only `kredibel` for rules and indexes;
  Cloud Build pins `firebase-tools` and waits for that database's indexes. Rules releases are checked
  by API, not by the CLI's message: it reports "released to cloud.firestore" while the release that
  changes is `cloud.firestore/kredibel`.

## Alternatives considered

| Option | Why not |
|---|---|
| Stay on `(default)` | Shares a database, its indexes and its rules release with other projects' leftovers |
| A separate GCP project | Clean, but new billing, IAM and Firebase setup during the competition |

## Consequences

- Firestore's daily free quota applies to one database per project. `kredibel` pays from the first
  read: USD 0.03 per 100K reads and 0.09 per 100K writes, cents at demo volumes
  ([`21`](../21-cost-analysis.md)).
- The workspace created on `(default)` was copied over (org, members, profile events, the signup
  registry); test uploads were not, and Kredibel's data was removed from `(default)`.
