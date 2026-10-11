---
name: data-migration
description: Changes the Kredibel Firestore data model safely, adding a field, renaming, changing a type or unit, splitting a collection, adding an index or moving Cloud Storage objects, with schemaVersion, an upcaster, a forward-only migration and the schema snapshot. Use whenever a persistence model, index or storage layout changes.
---

# Change the data model

Read `docs/22-data-migrations.md` first; this is the short form.

1. **Classify** the change with the table in docs/22 §2. Not breaking (new optional field with a
   correct default, new collection, new index)? Update the model, `docs/09-data-model.md`,
   indexes and the schema snapshot, and stop here.
2. **Breaking?** Plan two releases: expand now, contract later. Write both in the PR description.
3. **Model:** add `XxxDocVN` in `backend/app/adapters/firestore/models/` and bump
   `SCHEMA_VERSION`. Keep the old class for fixtures until the contract release.
4. **Upcaster (TDD):** add `@upcaster("<collection>", from_version=N-1)` in
   `adapters/firestore/upcasters/`; add a fixture of the old shape in
   `backend/tests/fixtures/firestore/<collection>/v<N-1>.json`; test that it upcasts to a valid VN.
5. **Migration (TDD):** `backend/migrations/NNNN_<slug>.py` reusing the upcaster as `transform`;
   set `requires_indexes` if the new code queries a new index. Tests: deterministic, idempotent,
   emulator run including an interrupted run.
6. **Contracts:** `make schema-snapshot`; update `contracts/firestore.indexes.json`, rules and
   `contracts/openapi.yaml` if affected; update `docs/09-data-model.md` in the same commit.
7. **Never** rewrite `events`, decisions, `runs`, `analysis/{runId}` or findings of past runs; read
   them through upcasters. Never rename a field in place or reuse a name with a new meaning.
8. **Release:** `make migrate-dry ENV=…` and read the counts and sample diffs; Cloud Build deploys
   indexes, exports, runs the migration, then deploys services. Record the result in
   `docs/20-implementation-status.md`.
9. **Contract release:** remove old reads and the upcaster step, add a `cleanup` migration that
   deletes old fields, drop unused indexes, refresh the snapshot.
