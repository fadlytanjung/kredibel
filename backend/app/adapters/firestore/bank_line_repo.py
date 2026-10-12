"""BankLineRepository on Firestore (docs/09 §3.6): lines upserted by deterministic ID."""

from datetime import date
from decimal import Decimal

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.bank_line import BankLineDoc
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.models.bank_line import BankLine
from app.domain.models.events import AuditEvent
from app.ports.bank_line_repository import BankLineRepository

_BATCH = 400


def _to_doc(line: BankLine) -> BankLineDoc:
    return BankLineDoc(
        tx_id=line.tx_id,
        doc_id=line.doc_id,
        page=line.page,
        row_index=line.row_index,
        date=line.date.isoformat(),
        month=line.month,
        description=line.description,
        counterparty_name=line.counterparty_name,
        amount_minor=line.amount_minor,
        balance_minor=line.balance_minor,
        source=line.source,
        consensus=line.consensus,
        notes=line.notes,
        chunk_ids=list(line.chunk_ids),
        category=line.category,
        cashflow_class=line.cashflow_class,
        risk_tags=line.risk_tags,
        categorized_by=line.categorized_by,
        category_confidence=None
        if line.category_confidence is None
        else str(line.category_confidence),
        match={"state": line.match_state, "matchIds": line.match_ids},
        support=line.support,
    )


def _to_domain(doc: BankLineDoc) -> BankLine:
    return BankLine(
        tx_id=doc.tx_id,
        doc_id=doc.doc_id,
        page=doc.page,
        row_index=doc.row_index,
        date=date.fromisoformat(doc.date),
        month=doc.month,
        description=doc.description,
        amount=Decimal(doc.amount_minor) / 100,
        balance=None if doc.balance_minor is None else Decimal(doc.balance_minor) / 100,
        counterparty_name=doc.counterparty_name,
        source="WITNESS" if doc.source == "WITNESS" else "AI",
        consensus=doc.consensus,
        notes=doc.notes,
        chunk_ids=tuple(doc.chunk_ids),
        category=doc.category or "UNKNOWN",
        cashflow_class=doc.cashflow_class,
        risk_tags=doc.risk_tags,
        categorized_by=doc.categorized_by,
        category_confidence=None
        if doc.category_confidence is None
        else Decimal(doc.category_confidence),
        match_state=str(doc.match.get("state", "UNMATCHED")),
        match_ids=list(doc.match.get("matchIds") or []),
        support=doc.support,
    )


class FirestoreBankLineRepository(BankLineRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("bankLines")

    async def replace_document_lines(self, org_id: str, doc_id: str, lines: list[BankLine]) -> None:
        keep = {line.tx_id for line in lines}
        stale = [
            snap.reference
            async for snap in self._col(org_id)
            .where(filter=FieldFilter("docId", "==", doc_id))
            .stream()
            if snap.id not in keep
        ]
        writes = [("set", line) for line in lines] + [("delete", ref) for ref in stale]
        for start in range(0, len(writes), _BATCH):
            batch = self._db.batch()
            for kind, item in writes[start : start + _BATCH]:
                if kind == "set":
                    assert isinstance(item, BankLine)
                    batch.set(
                        self._col(org_id).document(item.tx_id), dump(_to_doc(item)), merge=True
                    )
                else:
                    batch.delete(item)  # type: ignore[arg-type]
            await batch.commit()

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        query = self._col(org_id).where(filter=FieldFilter("docId", "==", doc_id))
        refs = [snap.reference async for snap in query.stream()]
        for start in range(0, len(refs), _BATCH):
            batch = self._db.batch()
            for ref in refs[start : start + _BATCH]:
                batch.update(ref, {"heldAsDuplicate": held})
            await batch.commit()

    async def set_support(
        self, org_id: str, updates: dict[str, tuple[str, list[str], str]]
    ) -> None:
        items = sorted(updates.items())
        for start in range(0, len(items), _BATCH):
            batch = self._db.batch()
            for tx_id, (state, match_ids, support) in items[start : start + _BATCH]:
                batch.update(
                    self._col(org_id).document(tx_id),
                    {"match": {"state": state, "matchIds": match_ids}, "support": support},
                )
            await batch.commit()

    async def set_category(self, org_id: str, line: BankLine, event: AuditEvent) -> None:
        batch = self._db.batch()
        batch.update(
            self._col(org_id).document(line.tx_id),
            {
                "category": line.category,
                "cashflowClass": line.cashflow_class,
                "categorizedBy": line.categorized_by,
                "categoryConfidence": None,
            },
        )
        batch.set(
            self._db.collection("orgs").document(org_id).collection("events").document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def get_line(self, org_id: str, tx_id: str) -> BankLine | None:
        snap = await self._col(org_id).document(tx_id).get()
        return _to_domain(BankLineDoc.model_validate(snap.to_dict())) if snap.exists else None

    async def list_lines(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 500
    ) -> list[BankLine]:
        query = self._col(org_id)
        if doc_id:
            query = query.where(filter=FieldFilter("docId", "==", doc_id))
        if month:
            query = query.where(filter=FieldFilter("month", "==", month))
        lines = [
            _to_domain(BankLineDoc.model_validate(s.to_dict()))
            async for s in query.limit(limit).stream()
        ]
        return sorted(lines, key=lambda ln: (ln.date, ln.doc_id, ln.row_index))
