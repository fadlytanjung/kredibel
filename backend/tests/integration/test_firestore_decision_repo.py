"""Decisions on Firestore (docs/09 §3.12a): each decision is written with its audit event."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.decision_repo import FirestoreDecisionRepository
from app.domain.models.decision import Decision
from app.domain.models.events import AuditEvent, EventType

AT = datetime(2026, 4, 2, 9, 0, tzinfo=UTC)


@pytest.fixture
def db(firestore_emulator: str) -> AsyncClient:
    return AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")


def _event(decision: Decision, kind: EventType) -> AuditEvent:
    return AuditEvent(
        event_id=f"evt_{decision.decision_id}_{kind}",
        type=kind,
        actor_uid="u-1",
        actor_role="owner",
        at=AT,
        subject={"decisionId": decision.decision_id},
    )


async def test_a_decision_round_trips_with_its_event(db):
    repo = FirestoreDecisionRepository(db)
    paid = Decision(
        "dec_1",
        "PAYMENT_CONFIRMATION",
        "u-1",
        AT,
        invoice_id="inv_1",
        doc_id="doc_1",
        amount=Decimal("5000000.00"),
        currency="IDR",
        paid_on=date(2026, 3, 20),
        method="TRANSFER",
        reason="Paid from the owner's account",
        months=["2026-03"],
    )
    await repo.save("org_1", paid, _event(paid, "DECISION_RECORDED"))
    assert await repo.get("org_1", "dec_1") == paid
    assert [d.decision_id for d in await repo.list_decisions("org_1", record_id="inv_1")] == [
        "dec_1"
    ]
    events = [s.to_dict() async for s in db.collection("orgs/org_1/events").stream()]
    assert [e["type"] for e in events if e] == ["DECISION_RECORDED"]

    withdrawn = Decision(
        **{**paid.__dict__, "status": "WITHDRAWN", "withdrawn_by": "u-1", "withdrawn_at": AT}
    )
    await repo.save("org_1", withdrawn, _event(withdrawn, "DECISION_WITHDRAWN"))
    assert [d.status for d in await repo.list_decisions("org_1", status="WITHDRAWN")] == [
        "WITHDRAWN"
    ]
    assert await repo.list_decisions("org_1", status="ACTIVE") == []
