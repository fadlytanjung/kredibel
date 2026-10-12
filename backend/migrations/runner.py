"""Firestore migration runner with paging, checkpoints, lease locks, and status reporting.

Normative references: docs/22-data-migrations.md §4–§6 and docs/specs/001-foundation/tasks.md.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from google.cloud import firestore
from google.cloud.firestore_v1.field_path import FieldPath

from migrations import Migration, discover_migrations


class LockHeldError(Exception):
    """Raised when another runner currently holds system/migrationLock."""


# Takes the pending migration IDs, exports the database, returns the export's URI (docs/22 §8).
Exporter = Callable[[list[str]], str]


def managed_export(project: str, database: str, bucket: str) -> Exporter:
    """A managed Firestore export to the backups bucket, run as the migrate job's own service
    account (roles/datastore.importExportAdmin, docs/22 §6); it blocks until the export is done."""

    def export(migration_ids: list[str]) -> str:
        from google.cloud import firestore_admin_v1

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        uri = f"gs://{bucket}/{stamp}-{'-'.join(migration_ids)[:120]}"
        operation = firestore_admin_v1.FirestoreAdminClient().export_documents(
            request={
                "name": f"projects/{project}/databases/{database}",
                "output_uri_prefix": uri,
            }
        )
        operation.result(timeout=3000)
        return uri

    return export


class MigrationRunner:
    """Manages forward-only migrations against Cloud Firestore."""

    def __init__(
        self,
        db: firestore.Client | None = None,
        operator: str = "kredibel-operator",
        exporter: Exporter | None = None,
    ) -> None:
        if db is not None:
            self.db = db
        else:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "cloud-hack2skill")
            database = os.environ.get("FIRESTORE_DATABASE", "(default)")
            self.db = firestore.Client(project=project_id, database=database)
        self.operator = operator
        self.exporter = exporter
        self.backup_uri: str | None = None

    @property
    def lock_ref(self) -> firestore.DocumentReference:
        return self.db.collection("system").document("migrationLock")

    def migration_ref(self, migration_id: str) -> firestore.DocumentReference:
        return (
            self.db.collection("system")
            .document("migrations")
            .collection("records")
            .document(migration_id)
        )

    def acquire_lock(self, timeout_minutes: int = 10) -> None:
        """Acquire migration lock lease or raise LockHeldError."""
        lock_doc = self.lock_ref.get()
        now = datetime.now(UTC)

        if lock_doc.exists:
            data = lock_doc.to_dict() or {}
            holder = data.get("holder")
            lease_str = data.get("leaseUntil")
            if lease_str and holder and holder != self.operator:
                lease_time = datetime.fromisoformat(lease_str)
                if lease_time > now:
                    raise LockHeldError(
                        f"Another migration runner ({holder}) holds the lock until {lease_str}."
                    )

        lease_until = (now + timedelta(minutes=timeout_minutes)).isoformat()
        self.lock_ref.set({"holder": self.operator, "leaseUntil": lease_until})

    def release_lock(self) -> None:
        """Release the migration lock."""
        self.lock_ref.delete()

    def renew_lock(self, timeout_minutes: int = 10) -> None:
        """Renew lock lease during long operations."""
        now = datetime.now(UTC)
        lease_until = (now + timedelta(minutes=timeout_minutes)).isoformat()
        self.lock_ref.set({"holder": self.operator, "leaseUntil": lease_until}, merge=True)

    def run_migration(
        self,
        migration: Migration,
        dry_run: bool = False,
        limit: int | None = None,
        page_size: int = 300,
    ) -> dict[str, Any]:
        """Apply a single migration with paging, checkpoints, and idempotency."""
        m_ref = self.migration_ref(migration.id)
        m_doc = m_ref.get()

        if m_doc.exists:
            existing = m_doc.to_dict() or {}
            if existing.get("status") == "DONE":
                return {
                    "id": migration.id,
                    "status": "SKIPPED",
                    "reason": "Already DONE",
                    "processed": existing.get("processed", 0),
                    "updated": existing.get("updated", 0),
                    "skipped": existing.get("skipped", 0),
                    "failed": existing.get("failed", 0),
                }

        # Check for checkpoint resume
        cursor: str | None = None
        processed = 0
        updated = 0
        skipped = 0
        failed = 0

        if m_doc.exists:
            existing = m_doc.to_dict() or {}
            if existing.get("status") == "RUNNING":
                cursor = existing.get("cursor")
                processed = existing.get("processed", 0)
                updated = existing.get("updated", 0)
                skipped = existing.get("skipped", 0)
                failed = existing.get("failed", 0)

        started_at = datetime.now(UTC).isoformat()
        if not dry_run:
            m_ref.set(
                {
                    "id": migration.id,
                    "status": "RUNNING",
                    "startedAt": started_at,
                    "dryRun": dry_run,
                    "operator": self.operator,
                    "backupUri": self.backup_uri,
                },
                merge=True,
            )

        # Query collection group ordered by document ID (__name__)
        while True:
            query = (
                self.db.collection_group(migration.collection_group)
                .order_by(FieldPath.document_id())
                .limit(page_size)
            )
            if cursor:
                query = query.start_after([cursor])

            docs = list(query.stream())
            if not docs:
                break

            for doc in docs:
                if limit and processed >= limit:
                    break

                processed += 1
                doc_data = doc.to_dict() or {}
                doc_ver = doc_data.get("schemaVersion")
                if doc_ver is None:
                    doc_ver = doc_data.get("schema_version", 1)

                if int(doc_ver) >= migration.to_version:
                    skipped += 1
                    cursor = doc.id
                    continue

                try:
                    transformed = migration.transform(doc_data)
                    transformed["schemaVersion"] = migration.to_version
                    if not dry_run:
                        doc.reference.set(transformed)
                    updated += 1
                except Exception:
                    failed += 1

                cursor = doc.id

            # Save checkpoint
            if not dry_run and cursor:
                m_ref.set(
                    {
                        "cursor": cursor,
                        "processed": processed,
                        "updated": updated,
                        "skipped": skipped,
                        "failed": failed,
                    },
                    merge=True,
                )

            self.renew_lock()

            if limit and processed >= limit:
                # Interrupted / hit limit before finishing all records
                return {
                    "id": migration.id,
                    "status": "RUNNING",
                    "processed": processed,
                    "updated": updated,
                    "skipped": skipped,
                    "failed": failed,
                    "cursor": cursor,
                }

        # Mark finished
        finished_status = "DONE" if failed == 0 else "FAILED"
        finished_record = {
            "id": migration.id,
            "status": finished_status,
            "kind": migration.kind,
            "collectionGroup": migration.collection_group,
            "fromVersion": migration.from_version,
            "toVersion": migration.to_version,
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "dryRun": dry_run,
            "operator": self.operator,
            "finishedAt": datetime.now(UTC).isoformat(),
        }
        if not dry_run:
            m_ref.set(finished_record, merge=True)

        return finished_record

    def run_all(
        self,
        dry_run: bool = False,
        limit: int | None = None,
        only_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run all discovered migrations sequentially under lock. A real run with pending migrations
        takes the export first, so a bad migration has a precise restore point (docs/22 §7)."""
        self.acquire_lock()
        results: list[dict[str, Any]] = []
        try:
            pending = self.pending(only_id)
            if pending and not dry_run and self.exporter is not None:
                self.backup_uri = self.exporter([m.id for m in pending])
                print(f"Exported the database to {self.backup_uri}")
            migrations = discover_migrations()
            for m in migrations:
                if only_id and m.id != only_id:
                    continue
                res = self.run_migration(m, dry_run=dry_run, limit=limit)
                results.append(res)
                if res.get("status") == "FAILED":
                    break
        finally:
            self.release_lock()
        return results

    def pending(self, only_id: str | None = None) -> list[Migration]:
        """Migrations not yet DONE, in order."""
        out: list[Migration] = []
        for m in discover_migrations():
            if only_id and m.id != only_id:
                continue
            doc = self.migration_ref(m.id).get()
            if not (doc.exists and (doc.to_dict() or {}).get("status") == "DONE"):
                out.append(m)
        return out

    def get_status(self) -> list[dict[str, Any]]:
        """Return status of all registered migrations."""
        migrations = discover_migrations()
        statuses: list[dict[str, Any]] = []

        for m in migrations:
            doc = self.migration_ref(m.id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                statuses.append(
                    {
                        "id": m.id,
                        "status": data.get("status", "PENDING"),
                        "updated": data.get("updated", 0),
                        "processed": data.get("processed", 0),
                        "finishedAt": data.get("finishedAt"),
                    }
                )
            else:
                statuses.append(
                    {
                        "id": m.id,
                        "status": "PENDING",
                        "updated": 0,
                        "processed": 0,
                        "finishedAt": None,
                    }
                )

        return statuses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kredibel Firestore migration runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "status"],
        help="Command to execute (run or status)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run migration without writing")
    parser.add_argument("--status", action="store_true", help="Print migration status")
    parser.add_argument("--limit", type=int, help="Limit number of documents processed")
    parser.add_argument("--only", type=str, help="Run only specific migration ID")
    parser.add_argument("--env", type=str, default="local", help="Environment (local, prod, etc.)")
    args = parser.parse_args(argv)

    exporter = None
    if os.environ.get("MIGRATION_EXPORT_BEFORE_RUN", "").lower() == "true":
        exporter = managed_export(
            os.environ.get("GOOGLE_CLOUD_PROJECT", "cloud-hack2skill"),
            os.environ.get("FIRESTORE_DATABASE", "(default)"),
            os.environ["BACKUPS_BUCKET"],
        )
    runner = MigrationRunner(exporter=exporter)

    if args.command == "status" or args.status:
        statuses = runner.get_status()
        print(f"\nMigration Status (env={args.env}):")
        print("-" * 60)
        for s in statuses:
            print(f"  {s['id']:<30} {s['status']:<10} processed: {s['processed']}")
        print("-" * 60)
        return 0

    print(f"Starting migrations (env={args.env}, dry_run={args.dry_run})...")
    results = runner.run_all(dry_run=args.dry_run, limit=args.limit, only_id=args.only)

    for r in results:
        print(f"Migration {r.get('id')}: {r.get('status')} (updated: {r.get('updated', 0)})")

    failed = any(r.get("status") == "FAILED" for r in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
