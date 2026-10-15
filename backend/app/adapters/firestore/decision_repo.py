"""DecisionRepository on Firestore: the decision and its audit event in one batch."""

from datetime import date
from decimal import Decimal

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.decision import DecisionDoc
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.models.decision import Decision
from app.domain.models.events import AuditEvent
from app.ports.decision_repository import DecisionRepository


def _to_doc(d: Decision) -> DecisionDoc:
    return DecisionDoc(
        decision_id=d.decision_id,
        kind=d.kind,
        status=d.status,
        doc_id=d.doc_id,
        invoice_id=d.invoice_id,
        receipt_id=d.receipt_id,
        tx_id=d.tx_id,
        record_id=d.record_id,
        amount_minor=None if d.amount is None else int(d.amount * 100),
        currency=d.currency,
        paid_on=d.paid_on.isoformat() if d.paid_on else None,
        method=d.method,
        reason=d.reason,
        printed_currency=d.printed_currency,
        months=d.months,
        decided_by=d.decided_by,
        decided_at=d.decided_at,
        withdrawn_by=d.withdrawn_by,
        withdrawn_at=d.withdrawn_at,
    )


def _to_domain(doc: DecisionDoc) -> Decision:
    return Decision(
        decision_id=doc.decision_id,
        kind=doc.kind,  # type: ignore[arg-type]
        decided_by=doc.decided_by,
        decided_at=doc.decided_at,
        status="WITHDRAWN" if doc.status == "WITHDRAWN" else "ACTIVE",
        doc_id=doc.doc_id,
        invoice_id=doc.invoice_id,
        receipt_id=doc.receipt_id,
        tx_id=doc.tx_id,
        amount=None if doc.amount_minor is None else Decimal(doc.amount_minor) / 100,
        currency=doc.currency,
        paid_on=date.fromisoformat(doc.paid_on) if doc.paid_on else None,
        method=doc.method,  # type: ignore[arg-type]
        reason=doc.reason,
        printed_currency=doc.printed_currency,
        months=doc.months,
        withdrawn_by=doc.withdrawn_by,
        withdrawn_at=doc.withdrawn_at,
    )


class FirestoreDecisionRepository(DecisionRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _org(self, org_id: str):
        return self._db.collection("orgs").document(org_id)

    async def save(self, org_id: str, decision: Decision, event: AuditEvent) -> None:
        org = self._org(org_id)
        batch = self._db.batch()
        batch.set(
            org.collection("decisions").document(decision.decision_id), dump(_to_doc(decision))
        )
        batch.set(
            org.collection("events").document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def get(self, org_id: str, decision_id: str) -> Decision | None:
        snap = await self._org(org_id).collection("decisions").document(decision_id).get()
        return _to_domain(DecisionDoc.model_validate(snap.to_dict())) if snap.exists else None

    async def list_decisions(
        self,
        org_id: str,
        *,
        kind: str | None = None,
        doc_id: str | None = None,
        record_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Decision]:
        query = self._org(org_id).collection("decisions")
        for field, value in (
            ("kind", kind),
            ("docId", doc_id),
            ("recordId", record_id),
            ("status", status),
        ):
            if value:
                query = query.where(filter=FieldFilter(field, "==", value))
        found = [
            _to_domain(DecisionDoc.model_validate(s.to_dict()))
            async for s in query.limit(limit).stream()
        ]
        return sorted(found, key=lambda d: (d.decided_at, d.decision_id), reverse=True)
