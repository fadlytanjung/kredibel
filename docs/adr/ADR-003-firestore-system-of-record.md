# ADR-003 — Firestore as the system of record

**Status:** Accepted · **Date:** 2026-10-10

## Context

We need durable storage for a workspace's documents, hundreds of bank lines, invoices, receipts and
ledger entries per month, matches, review items, findings, month results and an audit trail, plus a
way to push live progress to the browser. 7 build days; no
appetite for VPCs or connection pools.

## Decision

**Firestore (Native mode, `(default)` database, `asia-southeast1`)** for all structured data, with
subcollections per workspace; **Cloud Storage** for files and raw extractor output. The browser reads
progress fields through Firestore listeners; all writes go through the API (rules deny client writes).

## Alternatives considered

| Option | Why not (for now) |
|---|---|
| Cloud SQL for PostgreSQL | Strong for relational queries, but always-on: ≈ USD 9–17/month for the smallest shared-core instance (no SLA), ≈ USD 50/month for 1 dedicated vCPU; needs connectors and migrations; no realtime push |
| AlloyDB / Spanner | ≈ USD 227+/month and from ≈ USD 40/month respectively; far beyond this workload |
| BigQuery as primary | Analytical, not transactional; great later for portfolio analytics (P2 export) |
| Firestore for files too | 1 MiB document limit; GCS is the right place for binaries |

## Consequences

- Money stored as integer minor units; decimals as strings ([`09`](../09-data-model.md) §2).
- Writes are chunked (≤ 400 per batch); deterministic IDs make re-runs idempotent.
- Cross-workspace analytics (an accounting firm's clients) would need a BigQuery export (later).
- Assistant retrieval (P1) uses Firestore's own vector search, so no second store is added ([ADR-014](ADR-014-finance-assistant-tools-rag-memory.md)).
- Org isolation is enforced twice: API (claims) and rules (for client reads).

## Cost

The Firestore free quota (50K reads, 20K writes, 20K deletes, 1 GiB per day) covers about 20 full
analysis runs per day; beyond that a run costs ≈ USD 0.001 in Firestore operations. The free tier
applies to **one database per project**, so we use only `(default)`. Full comparison:
[`21-cost-analysis.md`](../21-cost-analysis.md) §2.
