"""Domain models for documents, pages, and duplicates (docs/09 §3.5).

Normative references: docs/09 §3.5, docs/10 §2.2, contracts/openapi.yaml.
Pure domain logic: no framework dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.domain.page_triage import TextLayerStatus, WitnessType


class DocType(StrEnum):
    BANK_STATEMENT = "BANK_STATEMENT"
    SALES_INVOICE = "SALES_INVOICE"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    RECEIPT = "RECEIPT"
    LEDGER_EXPORT = "LEDGER_EXPORT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DocStatus(StrEnum):
    UPLOADED = "UPLOADED"
    SCREENING = "SCREENING"
    READING = "READING"
    CHECKING = "CHECKING"
    DONE = "DONE"
    DUPLICATE = "DUPLICATE"
    NEEDS_INPUT = "NEEDS_INPUT"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class DuplicateKind(StrEnum):
    EXACT = "EXACT"
    CONTENT = "CONTENT"


class DuplicateDecision(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class PageStatus(StrEnum):
    PENDING = "PENDING"
    READING = "READING"
    DONE = "DONE"
    BLANK = "BLANK"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DuplicateInfo:
    kind: DuplicateKind
    code: str
    of_doc_id: str
    decision: DuplicateDecision
    review_item_id: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None


@dataclass(frozen=True)
class PageRecord:
    page_no: int
    image_path: str
    thumb_path: str
    sha256: str
    text_layer: TextLayerStatus
    blank: bool
    witness: WitnessType
    status: PageStatus = PageStatus.PENDING
    agreement: Decimal | None = None


@dataclass(frozen=True)
class Document:
    doc_id: str
    file_name: str
    content_type: str
    size_bytes: int
    page_count: int
    sha256: str
    gcs_path: str
    uploaded_by: str
    uploaded_at: datetime
    doc_type: DocType = DocType.UNKNOWN
    type_confidence: Decimal | None = None
    status: DocStatus = DocStatus.UPLOADED
    status_detail: str | None = None
    p_hash: str | None = None
    months: list[str] = field(default_factory=list)
    duplicate: DuplicateInfo | None = None
    held_as_duplicate: bool = False
    counts_against_limits: bool = True
    pages: list[PageRecord] = field(default_factory=list)
    reading: dict[str, Any] | None = None
    statement_meta: dict[str, Any] | None = None
    ledger_meta: dict[str, Any] | None = None
    pdf: dict[str, Any] | None = None
    integrity: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None
    screening: dict[str, Any] | None = None
    last_run_id: str | None = None
