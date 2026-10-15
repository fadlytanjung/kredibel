"""Workspace-local GL/reporting reads; an account decision and audit commit atomically."""

from datetime import date
from decimal import Decimal
from hashlib import sha256

from google.cloud.firestore import AsyncClient

from app.adapters.firestore.models.ledger import AccountClassificationDoc, LedgerEntryDoc
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.errors import DomainError
from app.domain.models.events import AuditEvent
from app.domain.profit_loss import Classification, LedgerRow


def check_version(data: dict) -> None:
    if data.get("schemaVersion", 1) != 1:
        raise DomainError(code="RETRY_LATER", status=503, title="Unsupported ledger schema")


class FirestoreLedgerRepository:
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _org(self, org_id: str):
        return self._db.collection("orgs").document(org_id)

    async def list_rows(self, org_id: str) -> list[LedgerRow]:
        result = []
        async for snap in self._org(org_id).collection("ledgerEntries").stream():
            data = snap.to_dict() or {}
            check_version(data)
            doc = LedgerEntryDoc.model_validate({**data, "entryId": snap.id, "orgId": org_id})
            result.append(
                LedgerRow(
                    entry_id=doc.entry_id,
                    doc_id=doc.doc_id,
                    row_number=doc.row_number,
                    date=date.fromisoformat(doc.date),
                    account_code=doc.account_code,
                    account_name=doc.account_name,
                    debit=Decimal(doc.debit_minor) / 100,
                    credit=Decimal(doc.credit_minor) / 100,
                    currency=doc.currency,
                    posting_status=doc.posting_status,
                    journal_id=doc.journal_id,
                    entry_kind=doc.entry_kind,
                    held_as_duplicate=doc.held_as_duplicate,
                    duplicate=doc.duplicate,
                )
            )
        return result

    async def save_rows(self, org_id: str, rows: list[LedgerRow]) -> None:
        if not rows:
            return
        org = self._org(org_id)
        for i in range(0, len(rows), 400):
            batch = self._db.batch()
            for row in rows[i : i + 400]:
                doc_ref = org.collection("ledgerEntries").document(row.entry_id)
                data = LedgerEntryDoc(
                    org_id=org_id,
                    entry_id=row.entry_id,
                    doc_id=row.doc_id,
                    row_number=row.row_number,
                    date=row.date.isoformat(),
                    account_code=row.account_code,
                    account_name=row.account_name,
                    debit_minor=int(row.debit * 100),
                    credit_minor=int(row.credit * 100),
                    currency=row.currency,
                    posting_status=row.posting_status,
                    journal_id=row.journal_id,
                    entry_kind=row.entry_kind,
                    held_as_duplicate=row.held_as_duplicate,
                    duplicate=row.duplicate,
                )
                batch.set(doc_ref, dump(data))
            await batch.commit()

    async def classifications(self, org_id: str) -> dict[str, Classification]:
        result = {}
        async for snap in self._org(org_id).collection("accountClassifications").stream():
            data = snap.to_dict() or {}
            check_version(data)
            doc = AccountClassificationDoc.model_validate(data)
            if doc.org_id != org_id:
                raise DomainError(code="RETRY_LATER", status=503, title="Invalid account scope")
            result[doc.account_code] = Classification(
                account_code=doc.account_code, pnl_line=doc.pnl_line, subledger=doc.subledger
            )
        return result

    async def confirm(self, org_id: str, classification: Classification, event: AuditEvent) -> None:
        key = sha256(classification.account_code.encode()).hexdigest()
        org = self._org(org_id)
        batch = self._db.batch()
        batch.set(
            org.collection("accountClassifications").document(key),
            dump(
                AccountClassificationDoc(
                    org_id=org_id,
                    **classification.model_dump(),
                    confirmed_by=event.actor_uid,
                    confirmed_at=event.at,
                )
            ),
        )
        batch.set(
            org.collection("events").document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def decide_duplicate(
        self, org_id: str, entry_ids: list[str], *, held: bool, decision: str, event: AuditEvent
    ) -> None:
        org = self._org(org_id)
        batch = self._db.batch()
        for entry_id in entry_ids:
            batch.update(
                org.collection("ledgerEntries").document(entry_id),
                {"heldAsDuplicate": held, "duplicate.decision": decision},
            )
        batch.set(
            org.collection("events").document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()
