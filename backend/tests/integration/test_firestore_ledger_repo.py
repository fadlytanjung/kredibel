"""AC-018-1/2: additive defaults, scope and atomic persisted classification/audit."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.ledger_repo import FirestoreLedgerRepository
from app.domain.errors import DomainError
from app.domain.models.events import AuditEvent
from app.domain.profit_loss import Classification


async def test_ac018_classification_and_audit_round_trip(firestore_emulator):
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    repo = FirestoreLedgerRepository(db)
    org = db.collection("orgs").document("org_test")
    await (
        org.collection("ledgerEntries")
        .document("entry_synthetic")
        .set(
            {
                "orgId": "org_test",
                "docId": "doc_synthetic",
                "rowNumber": 1,
                "date": "2026-03-01",
                "accountCode": "4000",
                "debitMinor": 0,
                "creditMinor": 123456,
            }
        )
    )
    rows = await repo.list_rows("org_test")
    assert rows[0].credit == Decimal("1234.56")
    assert rows[0].posting_status == "UNKNOWN" and rows[0].currency is None
    decision = Classification(account_code="4000", pnl_line="REVENUE", subledger="RECEIVABLES")
    event = AuditEvent(
        event_id="evt_test",
        type="ACCOUNT_CLASSIFIED",
        actor_uid="u_test",
        actor_role="owner",
        at=datetime(2026, 3, 2, tzinfo=UTC),
        subject={},
    )
    await repo.confirm("org_test", decision, event)
    assert (await repo.classifications("org_test"))["4000"] == decision
    assert await repo.classifications("org_other") == {}
    assert await repo.list_rows("org_other") == []
    assert (await org.collection("events").document("evt_test").get()).exists
    await org.collection("ledgerEntries").document("entry_synthetic").update({"schemaVersion": 2})
    with pytest.raises(DomainError, match="Unsupported ledger schema"):
        await repo.list_rows("org_test")
    db.close()


async def test_ac018_save_rows_persists_ledger_entries(firestore_emulator):
    from datetime import date

    from app.domain.profit_loss import LedgerRow

    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    repo = FirestoreLedgerRepository(db)
    new_rows = [
        LedgerRow(
            entry_id="row_1",
            doc_id="doc_a",
            row_number=1,
            date=date(2026, 3, 1),
            account_code="4000",
            account_name="Sales",
            debit=Decimal("0"),
            credit=Decimal("500.00"),
            currency="IDR",
            posting_status="POSTED",
            journal_id="J1",
            entry_kind="ACTIVITY",
        )
    ]
    await repo.save_rows("org_save_test", new_rows)
    loaded = await repo.list_rows("org_save_test")
    assert len(loaded) == 1
    assert loaded[0].entry_id == "row_1"
    assert loaded[0].credit == Decimal("500.00")
    assert loaded[0].posting_status == "POSTED"
    db.close()

