"""Integration tests for FirestoreMonthRepository against the emulator (AC-004-4, AC-004-5)."""

import uuid

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.month_repo import FirestoreMonthRepository
from app.domain.models.month import Month, MonthState


@pytest.fixture
def month_repo(firestore_emulator: str) -> tuple[FirestoreMonthRepository, str]:
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    repo = FirestoreMonthRepository(db)
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    return repo, org_id


@pytest.mark.asyncio
async def test_month_repo_bump_generation_and_get(month_repo):
    repo, org_id = month_repo

    # Bump generation on non-existent month creates it with generation 1
    gen1, m1 = await repo.bump_generation(org_id, "2026-03", dirty=True)
    assert gen1 == 1
    assert m1.month == "2026-03"
    assert m1.dirty is True
    assert m1.state == MonthState.COLLECTING

    # Bump again increments generation to 2
    gen2, m2 = await repo.bump_generation(org_id, "2026-03", dirty=True)
    assert gen2 == 2
    assert m2.generation == 2

    # Get retrieves the updated document
    fetched = await repo.get(org_id, "2026-03")
    assert fetched is not None
    assert fetched.generation == 2
    assert fetched.dirty is True


@pytest.mark.asyncio
async def test_month_repo_save_and_list(month_repo):
    repo, org_id = month_repo

    month1 = Month(month="2026-01", state=MonthState.RECONCILED, dirty=False, generation=1)
    month2 = Month(month="2026-02", state=MonthState.NEEDS_REVIEW, dirty=True, generation=3)

    await repo.save(org_id, month1)
    await repo.save(org_id, month2)

    months = await repo.list(org_id)
    assert len(months) == 2
    month_map = {m.month: m for m in months}
    assert month_map["2026-01"].state == MonthState.RECONCILED
    assert month_map["2026-02"].generation == 3
