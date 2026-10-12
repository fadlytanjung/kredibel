"""Invoices and receipts on Firestore (docs/09 §3.7): records by deterministic ID per document."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.base import FirestoreModel
from app.adapters.firestore.models.invoice import (
    InvoiceDoc,
    InvoiceLineDoc,
    PayToDoc,
    ReceiptDoc,
    ReceiptItemDoc,
)
from app.adapters.firestore.txn import dump
from app.domain.models.invoice import Invoice, InvoiceLine, Receipt, ReceiptItem, SupplyKind
from app.ports.record_repository import DocumentRecords

_BATCH = 400


def _minor(value: Decimal | None) -> int | None:
    return None if value is None else int(value * 100)


def _money(minor: int | None) -> Decimal | None:
    return None if minor is None else Decimal(minor) / 100


def _day(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def invoice_to_doc(inv: Invoice) -> InvoiceDoc:
    return InvoiceDoc(
        invoice_id=inv.invoice_id, doc_id=inv.doc_id, kind=inv.kind, number=inv.number,
        issuer_name=inv.issuer_name, issuer_tax_id=inv.issuer_tax_id, buyer_name=inv.buyer_name,
        buyer_tax_id=inv.buyer_tax_id,
        issue_date=inv.issue_date.isoformat() if inv.issue_date else None,
        due_date=inv.due_date.isoformat() if inv.due_date else None, month=inv.month,
        currency=inv.currency, subtotal_minor=_minor(inv.subtotal), tax_minor=_minor(inv.tax),
        total_minor=_minor(inv.total),
        pay_to=PayToDoc(bank_name=inv.pay_to_bank, account_masked=inv.pay_to_masked),
        lines=[
            InvoiceLineDoc(
                description=ln.description, qty=None if ln.quantity is None else str(ln.quantity),
                unit_price_minor=_minor(ln.unit_price), amount_minor=_minor(ln.amount),
            )
            for ln in inv.lines
        ],
        supply_kind=inv.supply_kind, pages=inv.pages, consensus=inv.consensus, notes=inv.notes,
    )  # fmt: skip


def _supply(value: str | None) -> SupplyKind | None:
    return value if value in ("GOODS", "SERVICES", "MIXED") else None  # type: ignore[return-value]


def invoice_from_doc(doc: InvoiceDoc) -> Invoice:
    return Invoice(
        invoice_id=doc.invoice_id, doc_id=doc.doc_id,
        kind="SALES" if doc.kind == "SALES" else "PURCHASE", number=doc.number,
        issuer_name=doc.issuer_name, buyer_name=doc.buyer_name, issue_date=_day(doc.issue_date),
        month=doc.month, total=_money(doc.total_minor), currency=doc.currency,
        issuer_tax_id=doc.issuer_tax_id, buyer_tax_id=doc.buyer_tax_id, due_date=_day(doc.due_date),
        subtotal=_money(doc.subtotal_minor), tax=_money(doc.tax_minor),
        pay_to_bank=doc.pay_to.bank_name, pay_to_masked=doc.pay_to.account_masked,
        supply_kind=_supply(doc.supply_kind),
        lines=[
            InvoiceLine(
                description=ln.description, quantity=None if ln.qty is None else Decimal(ln.qty),
                unit_price=_money(ln.unit_price_minor), amount=_money(ln.amount_minor),
            )
            for ln in doc.lines
        ],
        pages=doc.pages, consensus=doc.consensus, notes=doc.notes,
    )  # fmt: skip


def receipt_to_doc(r: Receipt) -> ReceiptDoc:
    return ReceiptDoc(
        receipt_id=r.receipt_id, doc_id=r.doc_id, merchant_name=r.merchant_name,
        merchant_tax_id=r.merchant_tax_id, number=r.number,
        date=r.date.isoformat() if r.date else None, time=r.time, month=r.month,
        currency=r.currency, total_minor=_minor(r.total), tax_minor=_minor(r.tax),
        payment_method=r.payment_method,
        items=[ReceiptItemDoc(description=i.description, amount_minor=_minor(i.amount))
               for i in r.items],
        pages=r.pages, consensus=r.consensus, notes=r.notes,
    )  # fmt: skip


def receipt_from_doc(doc: ReceiptDoc) -> Receipt:
    method = doc.payment_method if doc.payment_method in ("CASH", "CARD", "TRANSFER") else "UNKNOWN"
    return Receipt(
        receipt_id=doc.receipt_id, doc_id=doc.doc_id, merchant_name=doc.merchant_name,
        date=_day(doc.date), month=doc.month, total=_money(doc.total_minor), currency=doc.currency,
        merchant_tax_id=doc.merchant_tax_id, number=doc.number, time=doc.time,
        tax=_money(doc.tax_minor), payment_method=method,  # type: ignore[arg-type]
        items=[ReceiptItem(i.description, _money(i.amount_minor)) for i in doc.items],
        pages=doc.pages, consensus=doc.consensus, notes=doc.notes,
    )  # fmt: skip


class FirestoreRecordRepository[T, D: FirestoreModel](DocumentRecords[T]):
    """One document's records in one collection, written in batches; stale ones are deleted."""

    def __init__(
        self,
        db: AsyncClient,
        collection: str,
        *,
        model: type[D],
        record_id: Callable[[T], str],
        to_doc: Callable[[T], D],
        from_doc: Callable[[D], T],
        order: Callable[[T], Any],
    ) -> None:
        self._db = db
        self._collection = collection
        self._model = model
        self._id = record_id
        self._to_doc = to_doc
        self._from_doc = from_doc
        self._order = order

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection(self._collection)

    async def replace_for_document(self, org_id: str, doc_id: str, records: list[T]) -> None:
        keep = {self._id(r) for r in records}
        query = self._col(org_id).where(filter=FieldFilter("docId", "==", doc_id))
        stale = [snap.reference async for snap in query.stream() if snap.id not in keep]
        writes: list[tuple[str, Any]] = [("set", r) for r in records] + [
            ("delete", s) for s in stale
        ]
        for start in range(0, len(writes), _BATCH):
            batch = self._db.batch()
            for kind, item in writes[start : start + _BATCH]:
                if kind == "set":
                    ref = self._col(org_id).document(self._id(item))
                    batch.set(ref, dump(self._to_doc(item)), merge=True)
                else:
                    batch.delete(item)
            await batch.commit()

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        query = self._col(org_id).where(filter=FieldFilter("docId", "==", doc_id))
        refs = [snap.reference async for snap in query.stream()]
        for start in range(0, len(refs), _BATCH):
            batch = self._db.batch()
            for ref in refs[start : start + _BATCH]:
                batch.update(ref, {"heldAsDuplicate": held})
            await batch.commit()

    async def list_records(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 200
    ) -> list[T]:
        query = self._col(org_id)
        if doc_id:
            query = query.where(filter=FieldFilter("docId", "==", doc_id))
        if month:
            query = query.where(filter=FieldFilter("month", "==", month))
        found = [
            self._from_doc(self._model.model_validate(s.to_dict()))
            async for s in query.limit(limit).stream()
        ]
        return sorted(found, key=self._order)


def firestore_invoices(db: AsyncClient) -> FirestoreRecordRepository[Invoice, InvoiceDoc]:
    return FirestoreRecordRepository(
        db, "invoices", model=InvoiceDoc, record_id=lambda i: i.invoice_id,
        to_doc=invoice_to_doc, from_doc=invoice_from_doc,
        order=lambda i: (i.issue_date or date.min, i.doc_id, i.invoice_id),
    )  # fmt: skip


def firestore_receipts(db: AsyncClient) -> FirestoreRecordRepository[Receipt, ReceiptDoc]:
    return FirestoreRecordRepository(
        db, "receipts", model=ReceiptDoc, record_id=lambda r: r.receipt_id,
        to_doc=receipt_to_doc, from_doc=receipt_from_doc,
        order=lambda r: (r.date or date.min, r.doc_id, r.receipt_id),
    )  # fmt: skip
