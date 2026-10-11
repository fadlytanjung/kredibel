# ADR-013 — Versioned documents and forward-only, expand/contract migrations

**Status:** Accepted · **Date:** 2026-10-10

## Context

Firestore ([ADR-003](ADR-003-firestore-system-of-record.md)) has no schema, so nothing stops old and
new document shapes from living side by side, and nothing tells the code which shape it is reading.
The data model will change: P1 features add fields and collections, the assistant adds vectors,
reviewers will ask for renames, and a later product may move to a relational database. We need
changes that are:

- **safe while the app runs** (web and worker revisions roll over one at a time; there is no
  maintenance window during the competition demo);
- **repeatable and resumable** (a job that dies half-way is simply run again);
- **auditable** (who ran what, when, on how many documents) and never rewriting the audit trail;
- **cheap** (every read and write is billed; most migrations touch only a few thousand documents);
- **portable** (the same discipline should carry us to Cloud SQL or AlloyDB if we ever need it).

## Decision

1. **Every persisted document carries `schemaVersion`** (an integer per collection, starting at 1).
   Persistence models live in `backend/app/adapters/firestore/models/` (Pydantic, one class per
   collection and version). The domain never sees a persistence model.
2. **Read-path upcasters.** The repository passes every document through `upcast(collection, doc)`,
   a chain of pure functions `v1 → v2 → … → latest`. Code always works with the latest shape, even
   before a backfill has run. **Writes always write the latest version.**
3. **Forward-only migrations** in `backend/migrations/NNNN_<slug>.py`. Each declares its id,
   collection group, `from_version` → `to_version`, a pure `transform(doc) -> doc | None` and an
   optional `applies(doc) -> bool`. A shared runner pages through documents by `__name__`, writes in
   batches with an `update_time` precondition, skips documents already at `to_version` (idempotent),
   checkpoints its cursor and counts, supports `--dry-run`, and ramps writes following Firestore's
   500/50/5 guidance. There is no `down()`: we roll **forward** with a new migration, and restore
   from a backup only for data loss.
4. **Registry and lock** in `system/migrations/{id}` and `system/migrationLock` (server-only, like
   `system/signup`). A lease prevents two runners. Status, counts, cursor, git SHA and operator are
   recorded; a finished migration is never run again.
5. **Expand → migrate → contract.** A breaking change ships in at least two releases: (1) *expand*:
   add the new field, collection or index, read both shapes through the upcaster, write the new one;
   (2) *migrate*: backfill with a job; (3) *contract*: one release later, delete the old field and the
   upcaster step with a cleanup migration. Renames and type changes never happen in place.
6. **One runner, one place:** a Cloud Run **job** `kredibel-migrate` (same image,
   `APP_ROLE=migrate`) runs pending migrations. Cloud Build runs it between "deploy indexes" and
   "deploy services" for expand migrations, and on demand (`make migrate`) for contract migrations.
7. **Backups first.** Point-in-time recovery (7 days) and a daily scheduled backup (7-day retention)
   are on for `(default)`; a backfill or cleanup on a shared environment also takes a managed export
   to `gs://<PROJECT_ID>-kredibel-backups/<date>-<migrationId>/` before it starts.
8. **Never migrated:** audit events (`events`), resolved review decisions and per-run snapshots
   (`runs`, `analysis/{runId}`, findings of past runs). They are read through upcasters forever, or
   superseded by a new run. Policy changes are new policy files, not data migrations.
9. **Schema drift gate.** `contracts/data/schema-snapshot.json` (JSON Schema per collection and
   version, generated from the persistence models) is checked by `tools/checks/schema_drift.py`: a
   model change without a version bump, an upcaster and a migration fails `make check`.
10. **Portability rule.** Every document stores its parent IDs as fields (`orgId`, `docId`,
    `month`, `runId` where they apply), money as integer minor units, enums as strings and
    times as UTC timestamps. Each collection then maps to one table with foreign keys
    ([`docs/22`](../22-data-migrations.md) §11).

## Alternatives considered

| Option | Why not |
|---|---|
| No versions; tolerate missing fields in code | Every reader grows `if "x" in doc` branches; nobody knows when old shapes are gone |
| Big-bang migration scripts run by hand | Not resumable, not audited, easy to run twice or against the wrong project |
| Migrate lazily on read and never backfill | Old shapes live forever; queries and indexes on the new field miss old documents |
| Reversible migrations with `down()` | Doubles the work and is rarely correct after new writes; restore and roll-forward are clearer |
| A schema-enforcing store now (Cloud SQL, AlloyDB) | Always-on cost and slower to build ([`docs/21`](../21-cost-analysis.md) §2); the portability rule keeps the door open |
| Third-party migration frameworks for Firestore | Little gain over a 200-line runner we test with the emulator; one less dependency |

## Consequences

- Repositories have one more step (upcast) and every persistence model a version constant.
- Two releases for any breaking change: slower, but no downtime and no half-migrated reads.
- The `system/` collections gain two documents; rules already deny clients everything outside
  `orgs/`.
- A future move to PostgreSQL reuses the same transforms to build its first import, then Alembic
  takes over migrations there.
