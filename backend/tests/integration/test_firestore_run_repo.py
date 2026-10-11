"""Integration tests for FirestoreRunRepository against the emulator (AC-004-1, AC-004-3)."""

import uuid
from datetime import UTC, datetime

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.run_repo import FirestoreRunRepository
from app.domain.models.run import Run, RunKind, RunStage, RunStatus, StageStatus


@pytest.fixture
def run_repo(firestore_emulator: str) -> tuple[FirestoreRunRepository, str]:
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    repo = FirestoreRunRepository(db)
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    return repo, org_id


@pytest.mark.asyncio
async def test_run_repo_create_get_and_update(run_repo):
    repo, org_id = run_repo
    now = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
    run = Run(
        run_id="run_123",
        kind=RunKind.DOCUMENT,
        target="doc_abc",
        status=RunStatus.QUEUED,
        created_at=now,
    )

    await repo.create(org_id, run)
    fetched = await repo.get(org_id, "run_123")
    assert fetched is not None
    assert fetched.run_id == "run_123"
    assert fetched.kind == RunKind.DOCUMENT
    assert fetched.target == "doc_abc"
    assert fetched.status == RunStatus.QUEUED

    await repo.update_status(org_id, "run_123", RunStatus.DONE, ended=True)
    updated = await repo.get(org_id, "run_123")
    assert updated is not None
    assert updated.status == RunStatus.DONE
    assert updated.ended_at is not None


@pytest.mark.asyncio
async def test_run_repo_append_stage_and_list_by_target(run_repo):
    repo, org_id = run_repo
    now = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
    run = Run(
        run_id="run_456",
        kind=RunKind.DOCUMENT,
        target="doc_target",
        status=RunStatus.RUNNING,
        created_at=now,
    )
    await repo.create(org_id, run)

    stage = RunStage(
        node="inspect_file",
        status=StageStatus.DONE,
        summary="File inspected successfully",
    )
    await repo.append_stage(org_id, "run_456", stage)

    fetched = await repo.get(org_id, "run_456")
    assert fetched is not None
    assert len(fetched.stages) == 1
    assert fetched.stages[0].node == "inspect_file"
    assert fetched.stages[0].status == StageStatus.DONE

    listed = await repo.list_by_target(org_id, "doc_target")
    assert len(listed) == 1
    assert listed[0].run_id == "run_456"
