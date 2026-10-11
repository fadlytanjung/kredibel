"""FirestoreUsageRepository against the emulator (T013-07, AC-013-9, AC-013-10)."""

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.usage_repo import FirestoreUsageRepository
from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.adapters.policy_files import load_plans
from app.core.auth import Principal
from app.core.errors import PlanLimitReachedError
from app.domain.models.workspace import WorkspaceCreate
from app.domain.plans import UploadRequest
from app.ports.workspace_repository import PendingWrite, UsageSettlement
from app.services.entitlement_service import EntitlementService
from app.services.workspace_service import WorkspaceService
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
CLOCK = FixedClock(datetime(2026, 10, 11, 8, 0, tzinfo=UTC))


@pytest.fixture
async def org(firestore_emulator: str) -> tuple[AsyncClient, str]:
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    workspaces = WorkspaceService(
        repo=FirestoreWorkspaceRepository(db),
        identity=FakeIdentityAdmin(),
        plans=PLANS,
        clock=CLOCK,
        signup_mode="open",
        max_workspaces=15,
    )
    ws = await workspaces.create(
        Principal(uid="u-1"),
        WorkspaceCreate.model_validate(
            {"name": "Synthetic Ltd", "entityType": "COMPANY", "timezone": "Asia/Jakarta"}
        ),
    )
    return db, ws.org_id


def _service(db: AsyncClient) -> EntitlementService:
    return EntitlementService(
        repo=FirestoreUsageRepository(db), plans=PLANS, clock=CLOCK, run_quota_per_org_per_day=80
    )


async def test_ac013_9_two_uploads_at_the_limit_cannot_both_pass(org):
    db, org_id = org
    await db.document(f"orgs/{org_id}/usageMonthly/2026-10").set(
        {"orgId": org_id, "month": "2026-10", "documentsUploaded": 149, "schemaVersion": 1}
    )
    service = _service(db)
    upload = UploadRequest(size_bytes=1024, pages=1, pages_to_read=1)

    results = await asyncio.gather(
        service.reserve_upload(
            org_id, upload, (PendingWrite(f"orgs/{org_id}/documents/doc_a", {"n": 1}),)
        ),
        service.reserve_upload(
            org_id, upload, (PendingWrite(f"orgs/{org_id}/documents/doc_b", {"n": 2}),)
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(r, PlanLimitReachedError) for r in results) == 1
    month = (await db.document(f"orgs/{org_id}/usageMonthly/2026-10").get()).to_dict()
    assert month is not None and month["documentsUploaded"] == 150
    docs = [s.id async for s in db.collection(f"orgs/{org_id}/documents").stream()]
    assert len(docs) == 1, "the losing upload's document must not be written"


async def test_ac013_10_settlement_keeps_ai_spend_as_an_exact_decimal_string(org):
    db, org_id = org
    service = _service(db)
    await service.reserve_upload(org_id, UploadRequest(size_bytes=1024, pages=6, pages_to_read=6))

    for spend in ("0.0123", "0.0877"):
        await service.settle_document_run(
            org_id,
            UsageSettlement(
                month="2026-10",
                pages_reserved=3,
                pages_read=2,
                pages_cached=1,
                ocr_pages=0,
                parser_pages=0,
                ai_spend_usd=Decimal(spend),
            ),
        )

    month = (await db.document(f"orgs/{org_id}/usageMonthly/2026-10").get()).to_dict()
    assert month is not None
    assert month["aiSpendUsd"] == "0.1000"
    assert (month["pagesReserved"], month["pagesRead"], month["pagesCached"]) == (4, 4, 2)
