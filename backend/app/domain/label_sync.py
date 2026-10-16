"""A month's labels from what is stored (spec 016, AC-016-1, AC-016-2). Pure.

The workflow nodes write labels as they decide. This builds the same labels from the stored books,
so a month run keeps them current (a match that changed a line's category, a person's category on
the month page) and a workspace read before labels existed gets them: a CATEGORY label per
categorized bank line, a DOC_TYPE label per document, a FIELD_VALUE label per value the two readings
did not agree on. `changed` keeps only what is new or whose automatic value moved, so the
provenance a node wrote (model, prompt, run, span) is never replaced by a rebuilt copy, and people's
decisions win as everywhere else.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, cast

from app.domain.accounts import mask_numbers_in_text
from app.domain.categorize import CategoryPolicy
from app.domain.labels import (
    AiDecision,
    Label,
    LabelSubject,
    LearningPolicy,
    Source,
    decide,
    propose,
)
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocType, Document
from app.domain.models.invoice import Invoice, Receipt

# How a line's category was decided, as a label source.
SOURCE_OF: dict[str, Source] = {
    "MODEL": "MODEL",
    "RULE": "RULE",
    "MATCH": "MATCH",
    "TRANSFER": "MATCH",
    "USER": "PERSON",
}
UNSETTLED = ("CONFLICT", "SINGLE_SOURCE")


@dataclass(frozen=True)
class ReadRecord:
    """One record a page produced: its page, how it is named and the consensus of its values."""

    page: int
    title: str
    consensus: dict[str, Any]
    month: str | None
    tx_id: str | None = None


def first_line(text: str | None) -> str:
    return text.splitlines()[0] if text else ""


def line_records(lines: list[BankLine]) -> list[ReadRecord]:
    return [
        ReadRecord(ln.page, f"Row {ln.row_index}", dict(ln.consensus or {}), ln.month, ln.tx_id)
        for ln in lines
    ]


def document_records(noun: str, records: list[Invoice] | list[Receipt]) -> list[ReadRecord]:
    out: list[ReadRecord] = []
    for record in records:
        title = f"{noun} {record.number}" if record.number else noun
        by_page: dict[int, dict[str, Any]] = {}
        for name, info in (record.consensus or {}).items():
            if isinstance(info, dict):
                by_page.setdefault(int(info.get("page") or 1), {})[name] = info
        for page_no, consensus in sorted(by_page.items()):
            out.append(ReadRecord(page_no, title, consensus, record.month))
    return out


def model_reading(info: dict[str, Any]) -> str | None:
    raw = info.get("raw")
    value = raw.get("GEMINI") if isinstance(raw, dict) else None
    return str(value) if value is not None else None


def page_image(doc_id: str, page_no: int | None) -> str:
    return f"/api/documents/{doc_id}/pages/{page_no or 1}"


def extraction_path(doc_id: str, page_no: int | None) -> str:
    return f"/api/documents/{doc_id}/pages/{page_no or 1}/extraction.md"


def value_labels(
    doc_id: str,
    file_name: str,
    records: list[ReadRecord],
    *,
    decision: Callable[[str], AiDecision],
    policy: LearningPolicy,
) -> list[Label]:
    """AC-016-1: a value the two readings did not agree on is a label asking a person; it holds the
    model's reading as printed, masked like every stored number."""
    out: list[Label] = []
    for record in records:
        for name, info in record.consensus.items():
            if not isinstance(info, dict) or info.get("status") not in UNSETTLED:
                continue
            out.append(
                propose(
                    "FIELD_VALUE",
                    LabelSubject(
                        display=f"{file_name}, {record.title.lower()} · {name}",
                        doc_id=doc_id,
                        page_no=record.page,
                        field=name,
                        tx_id=record.tx_id,
                    ),
                    decision(mask_numbers_in_text(model_reading(info) or "")),
                    policy=policy,
                    month=record.month,
                    page_image_url=page_image(doc_id, record.page),
                    extraction_url=extraction_path(doc_id, record.page),
                )
            )
    return out


def _decided_by_person(label: Label, by: str | None, at: datetime | None) -> Label:
    """A label whose value a person set elsewhere (the month page, the type item)."""
    decided = decide(
        label, action="CONFIRM", by=by or "", at=at or label.ai.at, policy=_NO_THRESHOLDS
    )
    return replace(decided, decided_by=by or None, decided_at=at)


_NO_THRESHOLDS = LearningPolicy(needs_check_below={})


def category_label(
    line: BankLine,
    *,
    at: datetime,
    policy: LearningPolicy,
    categories: CategoryPolicy,
    framework: str,
) -> Label | None:
    if line.category in ("", "UNKNOWN") or line.categorized_by not in SOURCE_OF:
        return None
    source = SOURCE_OF[line.categorized_by]
    category = categories.categories.get(line.category)
    label = propose(
        "CATEGORY",
        LabelSubject(
            display=first_line(line.description) or line.tx_id,
            doc_id=line.doc_id,
            page_no=line.page,
            tx_id=line.tx_id,
            counterparty_id=line.counterparty_id,
        ),
        AiDecision(
            value=line.category,
            source=source,
            at=at,
            confidence=line.category_confidence if source == "MODEL" else None,
        ),
        policy=policy,
        month=line.month,
        framework=framework,
        cashflow_class=(
            category.cashflow_class("US_GAAP" if framework == "US_GAAP" else "IFRS")
            if category
            else None
        ),
        page_image_url=page_image(line.doc_id, line.page),
        extraction_url=extraction_path(line.doc_id, line.page),
        example_text=mask_numbers_in_text(first_line(line.description)) or None,
    )
    if source == "PERSON":
        label = _decided_by_person(label, None, None)
    return label


def doc_type_label(doc: Document, *, at: datetime, policy: LearningPolicy) -> Label | None:
    if doc.doc_type == DocType.UNKNOWN:
        return None
    label = propose(
        "DOC_TYPE",
        LabelSubject(display=doc.file_name, doc_id=doc.doc_id, page_no=1),
        AiDecision(value=doc.doc_type.value, source="MODEL", at=at, confidence=doc.type_confidence),
        policy=policy,
        page_image_url=page_image(doc.doc_id, 1),
    )
    if doc.type_set_by:
        label = _decided_by_person(label, doc.type_set_by, None)
    return label


def month_labels(
    *,
    lines: list[BankLine],
    docs: list[Document],
    invoices: list[Invoice],
    receipts: list[Receipt],
    policy: LearningPolicy,
    categories: CategoryPolicy,
    framework: str,
    at: datetime,
) -> list[Label]:
    """Every label the month's stored books imply, deterministic for the same inputs."""
    by_doc = {d.doc_id: d for d in docs}
    out: list[Label] = []
    for line in lines:
        label = category_label(
            line, at=at, policy=policy, categories=categories, framework=framework
        )
        if label is not None:
            out.append(label)
    for doc in docs:
        label = doc_type_label(doc, at=at, policy=policy)
        if label is not None:
            out.append(label)

    def ai(value: str) -> AiDecision:
        return AiDecision(value=value, source="MODEL", at=at)

    for doc_id in sorted({line.doc_id for line in lines}):
        doc = by_doc.get(doc_id)
        if doc is None:
            continue
        records = line_records([line for line in lines if line.doc_id == doc_id])
        out += value_labels(doc_id, doc.file_name, records, decision=ai, policy=policy)
    for noun, records in (("Invoice", invoices), ("Receipt", receipts)):
        for doc_id in sorted({r.doc_id for r in records}):
            doc = by_doc.get(doc_id)
            if doc is None:
                continue
            mine = cast(Any, [r for r in records if r.doc_id == doc_id])
            out += value_labels(
                doc_id, doc.file_name, document_records(noun, mine), decision=ai, policy=policy
            )
    return sorted({lb.label_id: lb for lb in out}.values(), key=lambda lb: lb.label_id)


def changed(fresh: list[Label], existing: dict[str, Label], *, at: datetime) -> list[Label]:
    """What to write: labels not stored yet, labels whose automatic value moved, and a person's
    value set elsewhere over a label still proposed. Everything else is left as stored."""
    out: list[Label] = []
    for label in fresh:
        stored = existing.get(label.label_id)
        if stored is None:
            out.append(label)
            continue
        if label.final_source == "PERSON":
            if stored.status == "AI_PROPOSED":
                value = label.final_value
                action = "CONFIRM" if value == stored.ai.value else "CORRECT"
                decided = decide(
                    stored, action=action, by="", at=at, policy=_NO_THRESHOLDS, value=value
                )
                out.append(replace(decided, decided_by=label.decided_by))
            continue
        if stored.ai.value != label.ai.value:
            out.append(label)
    return out
