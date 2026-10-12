"""Tests for Firestore migration runner and 0000_example migration (AC-001-20)."""

from datetime import UTC, datetime, timedelta

import pytest
from google.cloud import firestore

from migrations import Migration, discover_migrations
from migrations.runner import LockHeldError, MigrationRunner


@pytest.fixture
def firestore_db(firestore_emulator: str):
    """Firestore emulator client fixture."""
    db = firestore.Client(project="cloud-hack2skill")
    # Clean lock and test records
    db.collection("system").document("migrationLock").delete()
    for test_id in ("0000_example_test", "0000_resume_test"):
        db.collection("system").document("migrations").collection("records").document(
            test_id
        ).delete()
    yield db
    db.collection("system").document("migrationLock").delete()
    for test_id in ("0000_example_test", "0000_resume_test"):
        db.collection("system").document("migrations").collection("records").document(
            test_id
        ).delete()


def test_ac001_20_discover_migrations():
    """Discovers migrations including 0000_example."""
    migrations = discover_migrations()
    assert len(migrations) >= 1
    assert any(m.id == "0000_example" for m in migrations)


def test_ac001_20_runner_lock_conflict(firestore_db):
    """Runner refuses to start when another runner holds system/migrationLock."""
    runner = MigrationRunner(db=firestore_db, operator="test-runner-1")

    # Set lock held by someone else in the future
    lock_ref = firestore_db.collection("system").document("migrationLock")
    future = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    lock_ref.set({"holder": "other-operator", "leaseUntil": future})

    try:
        with pytest.raises(LockHeldError):
            runner.acquire_lock()
    finally:
        # Clean up lock
        lock_ref.delete()


def test_ac001_20_run_applies_and_records_migration(firestore_db):
    """Runner applies 0000_example, records status DONE with counts, and skips second run."""
    runner = MigrationRunner(db=firestore_db, operator="test-runner")

    # Seed 3 documents in example_items
    coll = firestore_db.collection("example_items")
    doc1 = coll.document("item_1")
    doc2 = coll.document("item_2")
    doc3 = coll.document("item_3")

    doc1.set({"name": "Item 1", "schemaVersion": 1})
    doc2.set({"name": "Item 2", "schemaVersion": 1})
    doc3.set({"name": "Item 3", "schemaVersion": 2})  # Already v2

    migration = Migration(
        id="0000_example_test",
        description="Test migration",
        kind="backfill",
        collection_group="example_items",
        from_version=1,
        to_version=2,
        transform=lambda d: {**d, "migrated": True, "schemaVersion": 2},
    )

    # First run
    res = runner.run_migration(migration)
    assert res["status"] == "DONE"
    assert res["updated"] == 2
    assert res["skipped"] == 1

    # Verify document 1 was migrated
    updated_doc1 = doc1.get().to_dict()
    assert updated_doc1["migrated"] is True
    assert updated_doc1["schemaVersion"] == 2

    # Second run is skipped because already DONE
    res_second = runner.run_migration(migration)
    assert res_second["status"] == "SKIPPED"


def test_ac001_20_resumes_from_checkpoint(firestore_db):
    """Runner resumes from checkpoint after being interrupted half-way."""
    runner = MigrationRunner(db=firestore_db, operator="test-runner-resume")

    coll = firestore_db.collection("example_resume_items")
    for i in range(5):
        coll.document(f"item_{i}").set({"index": i, "schemaVersion": 1})

    migration = Migration(
        id="0000_resume_test",
        description="Test resume migration",
        kind="backfill",
        collection_group="example_resume_items",
        from_version=1,
        to_version=2,
        transform=lambda d: {**d, "resumed": True, "schemaVersion": 2},
    )

    # Simulate interrupted run: page_size=2, limit=2
    interrupted_res = runner.run_migration(migration, page_size=2, limit=2)
    assert interrupted_res["status"] == "RUNNING"
    assert interrupted_res["processed"] == 2

    # Resume run without limit
    resumed_res = runner.run_migration(migration, page_size=2)
    assert resumed_res["status"] == "DONE"
    assert resumed_res["processed"] == 5
    assert resumed_res["updated"] == 5


def test_ac001_22_cli_status(firestore_db, capsys):
    """CLI status command reports registered migrations."""
    from migrations.runner import main

    code = main(["status"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Migration Status" in captured.out
    assert "0000_example" in captured.out


def test_ac001_22_cli_dry_run(firestore_db, capsys):
    """CLI run with --dry-run operates without writing."""
    from migrations.runner import main

    code = main(["run", "--dry-run", "--only", "0000_example"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Starting migrations" in captured.out
    assert "dry_run=True" in captured.out


def _exports(firestore_db, monkeypatch, migrations):
    calls: list[list[str]] = []

    def exporter(ids: list[str]) -> str:
        calls.append(ids)
        return "gs://backups/20261012-" + "-".join(ids)

    monkeypatch.setattr("migrations.runner.discover_migrations", lambda: migrations)
    return MigrationRunner(db=firestore_db, operator="test-runner", exporter=exporter), calls


def _noop(test_id: str) -> Migration:
    return Migration(
        id=test_id,
        description="test",
        kind="backfill",
        collection_group="noSuchGroup",
        from_version=1,
        to_version=2,
        transform=lambda doc: doc,
    )


def test_a_real_run_with_pending_migrations_exports_first(firestore_db, monkeypatch):
    runner, calls = _exports(firestore_db, monkeypatch, [_noop("0000_example_test")])
    [result] = runner.run_all()
    assert calls == [["0000_example_test"]]
    assert result["status"] == "DONE"
    record = runner.migration_ref("0000_example_test").get().to_dict() or {}
    assert record["backupUri"] == "gs://backups/20261012-0000_example_test"


def test_no_export_for_a_dry_run_or_when_nothing_is_pending(firestore_db, monkeypatch):
    runner, calls = _exports(firestore_db, monkeypatch, [_noop("0000_example_test")])
    runner.run_all(dry_run=True)
    assert calls == []
    runner.run_all()
    runner.run_all()  # now DONE: nothing pending
    assert calls == [["0000_example_test"]]
