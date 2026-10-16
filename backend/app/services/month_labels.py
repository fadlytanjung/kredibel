"""Write a month's labels from its stored books (spec 016): the month run calls it after every
finalized month, and the Labels page's "create labels from your books" calls it for every month.
Only new labels and moved automatic values are written; people's decisions win."""

from datetime import datetime

from app.domain.categorize import CategoryPolicy
from app.domain.label_sync import changed, month_labels
from app.domain.labels import Label, LearningPolicy
from app.domain.models.document import DocStatus
from app.domain.models.invoice import Invoice, Receipt
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_repository import DocumentRepository
from app.ports.label_repository import LabelRepository
from app.ports.record_repository import DocumentRecords

_NOT_READ = (DocStatus.DUPLICATE, DocStatus.QUARANTINED, DocStatus.FAILED)


async def sync_month_labels(
    *,
    org_id: str,
    month: str,
    labels: LabelRepository,
    lines: BankLineRepository,
    documents: DocumentRepository,
    invoices: DocumentRecords[Invoice] | None,
    receipts: DocumentRecords[Receipt] | None,
    policy: LearningPolicy,
    categories: CategoryPolicy,
    framework: str,
    at: datetime,
    existing: dict[str, Label] | None = None,
) -> int:
    """The number of labels written for the month."""
    month_lines = await lines.list_lines(org_id, month=month, limit=5000)
    docs, _ = await documents.list_documents(org_id, limit=500)
    month_docs = [d for d in docs if month in d.months and d.status not in _NOT_READ]
    month_invoices = await invoices.list_records(org_id, month=month) if invoices else []
    month_receipts = await receipts.list_records(org_id, month=month) if receipts else []
    fresh = month_labels(
        lines=month_lines,
        docs=month_docs,
        invoices=list(month_invoices),
        receipts=list(month_receipts),
        policy=policy,
        categories=categories,
        framework=framework,
        at=at,
    )
    if existing is None:
        existing = {lb.label_id: lb for lb in await labels.list_labels(org_id, limit=None)}
    to_write = changed(fresh, existing, at=at)
    if to_write:
        stored = await labels.upsert(org_id, to_write)
        existing.update({lb.label_id: lb for lb in stored})
    return len(to_write)
