"""Unit tests for FindingService (spec 008, AC-008-9)."""

from datetime import UTC, datetime

import pytest

from app.core.auth import Principal
from app.domain.errors import NotFoundError, ValidationProblem
from app.domain.findings import Finding
from app.domain.models.month import Month, MonthState
from app.services.finding_service import FindingService, FindingUpdateRequest
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)


@pytest.fixture
def finding_service_deps():
    finding_repo = FakeFindingRepository()
    month_repo = FakeMonthRepository()
    doc_repo = FakeDocumentRepository()
    clock = FixedClock(NOW)
    service = FindingService(
        finding_repo=finding_repo,
        month_repo=month_repo,
        doc_repo=doc_repo,
        clock=clock,
    )
    return service, finding_repo, month_repo, doc_repo


@pytest.mark.asyncio
async def test_ac008_9_acknowledge_finding(finding_service_deps):
    service, finding_repo, month_repo, _ = finding_service_deps
    org_id = "org_1"
    principal = Principal(uid="user_1", org_id=org_id, role="owner")

    finding = Finding(
        finding_id="fnd_1234567890123456",
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="Balance break",
        facts={},
        evidence=[],
        scope="MONTH",
        month="2026-03",
        status="OPEN",
    )
    await finding_repo.save_finding(org_id, finding)

    month = Month(month="2026-03", state=MonthState.COLLECTING, dirty=False)
    await month_repo.save(org_id, month)

    updated = await service.update_finding(
        principal,
        "fnd_1234567890123456",
        FindingUpdateRequest(status="ACKNOWLEDGED"),
    )
    assert updated.status == "ACKNOWLEDGED"

    # Month is marked dirty for re-scoring (AC-008-9)
    saved_month = await month_repo.get(org_id, "2026-03")
    assert saved_month is not None
    assert saved_month.dirty is True


@pytest.mark.asyncio
async def test_ac008_9_dismiss_critical_finding_requires_reason(finding_service_deps):
    service, finding_repo, _, _ = finding_service_deps
    org_id = "org_1"
    principal = Principal(uid="user_1", org_id=org_id, role="owner")

    finding = Finding(
        finding_id="fnd_1234567890123456",
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="Balance break",
        facts={},
        evidence=[],
        scope="MONTH",
        month="2026-03",
        status="OPEN",
    )
    await finding_repo.save_finding(org_id, finding)

    # Missing reason
    with pytest.raises(ValidationProblem):
        await service.update_finding(
            principal,
            "fnd_1234567890123456",
            FindingUpdateRequest(status="DISMISSED", reason=None),
        )

    # Short reason (< 10 chars)
    with pytest.raises(ValidationProblem):
        await service.update_finding(
            principal,
            "fnd_1234567890123456",
            FindingUpdateRequest(status="DISMISSED", reason="too short"),
        )


@pytest.mark.asyncio
async def test_ac008_9_dismiss_critical_finding_with_valid_reason_succeeds(finding_service_deps):
    service, finding_repo, month_repo, _ = finding_service_deps
    org_id = "org_1"
    principal = Principal(uid="user_1", org_id=org_id, role="owner")

    finding = Finding(
        finding_id="fnd_1234567890123456",
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="Balance break",
        facts={},
        evidence=[],
        scope="MONTH",
        month="2026-03",
        status="OPEN",
    )
    await finding_repo.save_finding(org_id, finding)

    month = Month(month="2026-03", state=MonthState.COLLECTING, dirty=False)
    await month_repo.save(org_id, month)

    valid_reason = "Verified with the bank manager that this is a valid opening line adjustment."
    updated = await service.update_finding(
        principal,
        "fnd_1234567890123456",
        FindingUpdateRequest(status="DISMISSED", reason=valid_reason),
    )
    assert updated.status == "DISMISSED"
    assert updated.dismissal is not None
    assert updated.dismissal["by"] == "user_1"
    assert updated.dismissal["reason"] == valid_reason

    saved_month = await month_repo.get(org_id, "2026-03")
    assert saved_month is not None
    assert saved_month.dirty is True


@pytest.mark.asyncio
async def test_ac008_9_dismiss_low_severity_without_reason_succeeds(finding_service_deps):
    service, finding_repo, _, _ = finding_service_deps
    org_id = "org_1"
    principal = Principal(uid="user_1", org_id=org_id, role="owner")

    finding = Finding(
        finding_id="fnd_low_1234567890",
        code="R01_SALES_INVOICE_OVERDUE",
        category="RECONCILIATION",
        severity="LOW",
        title="Overdue invoice",
        facts={},
        evidence=[],
        scope="MONTH",
        month="2026-03",
        status="OPEN",
    )
    await finding_repo.save_finding(org_id, finding)

    updated = await service.update_finding(
        principal,
        "fnd_low_1234567890",
        FindingUpdateRequest(status="DISMISSED"),
    )
    assert updated.status == "DISMISSED"


@pytest.mark.asyncio
async def test_ac008_9_finding_not_found_raises_404(finding_service_deps):
    service, _, _, _ = finding_service_deps
    principal = Principal(uid="user_1", org_id="org_1", role="owner")

    with pytest.raises(NotFoundError):
        await service.update_finding(
            principal,
            "fnd_nonexistent123",
            FindingUpdateRequest(status="ACKNOWLEDGED"),
        )
