"""Labels: every AI decision a person can check (spec 016, ADR-016; docs/09 §3.19). Pure.

A label is born from an automatic decision (a model, a keyword rule, a match) and keeps the
latest one in `ai`. A person's confirmation or correction sets `final` and the status, and no later
run ever changes it: a re-run only updates `ai` and notes when it disagrees with the person.
"""

import hashlib
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from app.core.ids import content_id

Task = Literal["DOC_TYPE", "PAGE_TYPE", "CATEGORY", "COUNTERPARTY_ROLE", "FIELD_VALUE"]
Source = Literal["MODEL", "RULE", "MATCH", "PERSON"]
Status = Literal["AI_PROPOSED", "VERIFIED", "CORRECTED"]
DatasetUse = Literal["TRAIN", "EVAL", "EXCLUDED"]

TASKS: tuple[Task, ...] = ("DOC_TYPE", "PAGE_TYPE", "CATEGORY", "COUNTERPARTY_ROLE", "FIELD_VALUE")
NOT_CHECKED = "not checked by a person"


@dataclass(frozen=True)
class LearningPolicy:
    """contracts/policy/learning.v1.yaml: thresholds and the dataset split; never hard-coded."""

    needs_check_below: dict[str, Decimal]
    eval_share: Decimal = Decimal("0.20")
    examples_per_call: int = 5
    min_similarity: Decimal = Decimal("0.80")
    remembered_corrections: bool = True


@dataclass(frozen=True)
class LabelSubject:
    display: str
    doc_id: str | None = None
    page_no: int | None = None
    field: str | None = None
    tx_id: str | None = None
    counterparty_id: str | None = None


@dataclass(frozen=True)
class AiDecision:
    value: str
    source: Source
    at: datetime
    confidence: Decimal | None = None
    model: str | None = None
    prompt_version: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    rule_id: str | None = None  # a remembered correction that decided it (AC-016-7)


@dataclass(frozen=True)
class Label:
    label_id: str
    task: Task
    subject: LabelSubject
    ai: AiDecision
    final_value: str
    final_source: Source
    status: Status = "AI_PROPOSED"
    needs_check: bool = False
    month: str | None = None
    framework: str | None = None
    cashflow_class: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    note: str | None = None
    ai_disagrees_with_person: bool = False
    dataset_use: DatasetUse = "EXCLUDED"
    dataset_reason: str | None = NOT_CHECKED
    extraction_url: str | None = None
    page_image_url: str | None = None


@dataclass(frozen=True)
class WorkspaceRule:
    """A person's correction remembered for a counterparty and direction (docs/09 §3.20)."""

    rule_id: str
    counterparty_key: str  # counterparty id, or the folded name when there is none
    direction: Literal["in", "out"]
    category: str
    source_label_id: str
    created_by: str
    created_at: datetime
    active: bool = True


def subject_key(subject: LabelSubject) -> str:
    return "|".join(
        [
            subject.doc_id or "",
            str(subject.page_no or ""),
            subject.field or "",
            subject.tx_id or "",
            subject.counterparty_id or "",
        ]
    )


def label_id(task: Task, subject: LabelSubject) -> str:
    """lbl_ + 16 hex of the task and the subject: a re-run upserts the same label (AC-016-2)."""
    return content_id("lbl", task, subject_key(subject))


def rule_id(counterparty_key: str, direction: str) -> str:
    return content_id("rule", counterparty_key, direction)


def dataset_split(the_label_id: str, eval_share: Decimal) -> DatasetUse:
    """A fixed split by hash of the label ID: a label never changes side (learning.v1 dataset)."""
    digest = hashlib.sha1(the_label_id.encode(), usedforsecurity=False).hexdigest()
    share = Decimal(int(digest[:8], 16)) / Decimal(2**32)
    return "EVAL" if share < eval_share else "TRAIN"


def needs_check(task: Task, confidence: Decimal | None, policy: LearningPolicy) -> bool:
    """Below the task's threshold, or with no score at all, a person is asked (AC-016-3)."""
    threshold = policy.needs_check_below.get(task)
    if threshold is None:
        return False
    return confidence is None or confidence < threshold


def propose(
    task: Task,
    subject: LabelSubject,
    ai: AiDecision,
    *,
    policy: LearningPolicy,
    month: str | None = None,
    framework: str | None = None,
    cashflow_class: str | None = None,
    page_image_url: str | None = None,
    extraction_url: str | None = None,
) -> Label:
    """A fresh automatic decision as a label, before any merge with what is stored."""
    return Label(
        label_id=label_id(task, subject),
        task=task,
        subject=subject,
        ai=ai,
        final_value=ai.value,
        final_source=ai.source,
        status="AI_PROPOSED",
        needs_check=needs_check(task, ai.confidence, policy),
        month=month,
        framework=framework,
        cashflow_class=cashflow_class,
        page_image_url=page_image_url,
        extraction_url=extraction_url,
    )


def merge(existing: Label | None, fresh: Label) -> Label:
    """A re-run over a stored label: people win (AC-016-2). A decided label keeps its final value,
    status, person and note, takes the new AI decision, and says when the AI now disagrees."""
    if existing is None or existing.status == "AI_PROPOSED":
        return fresh
    return replace(
        existing,
        ai=fresh.ai,
        month=fresh.month or existing.month,
        framework=fresh.framework or existing.framework,
        cashflow_class=fresh.cashflow_class or existing.cashflow_class,
        page_image_url=fresh.page_image_url or existing.page_image_url,
        extraction_url=fresh.extraction_url or existing.extraction_url,
        ai_disagrees_with_person=fresh.ai.value != existing.final_value,
        needs_check=False,
    )


def decide(
    label: Label,
    *,
    action: Literal["CONFIRM", "CORRECT"],
    by: str,
    at: datetime,
    policy: LearningPolicy,
    value: str | None = None,
    note: str | None = None,
) -> Label:
    """A person confirms the AI's value (VERIFIED) or replaces it (CORRECTED); the label then counts
    for evals and, with consent, training, on a side fixed by its ID (AC-016-6)."""
    if action == "CORRECT":
        if not value or not value.strip():
            raise ValueError("A correction needs a value")
        final = value.strip()
        status: Status = "CORRECTED"
    else:
        final = label.final_value if label.status != "AI_PROPOSED" else label.ai.value
        status = "VERIFIED" if final == label.ai.value else "CORRECTED"
    return replace(
        label,
        final_value=final,
        final_source="PERSON",
        status=status,
        needs_check=False,
        decided_by=by,
        decided_at=at,
        note=(note or "").strip() or None,
        ai_disagrees_with_person=False,
        dataset_use=dataset_split(label.label_id, policy.eval_share),
        dataset_reason=None,
    )


def summarize(labels: list[Label]) -> dict[str, Any]:
    """The page's sentence: how many people checked and how often the AI was right (AC-016-5)."""
    verified = sum(1 for lb in labels if lb.status == "VERIFIED")
    corrected = sum(1 for lb in labels if lb.status == "CORRECTED")
    checked = verified + corrected
    return {
        "total": len(labels),
        "needsCheck": sum(1 for lb in labels if lb.needs_check),
        "verified": verified,
        "corrected": corrected,
        "aiAgreementOnChecked": round(verified / checked, 4) if checked else None,
        "byTask": {task: sum(1 for lb in labels if lb.task == task) for task in TASKS},
        "byStatus": {
            status: sum(1 for lb in labels if lb.status == status)
            for status in ("AI_PROPOSED", "VERIFIED", "CORRECTED")
        },
    }


def rule_for(
    label: Label, *, counterparty_key: str, direction: str, by: str, at: datetime
) -> WorkspaceRule:
    """ "Apply to similar lines": the corrected category remembered for the party and direction."""
    way: Literal["in", "out"] = "in" if direction == "in" else "out"
    return WorkspaceRule(
        rule_id=rule_id(counterparty_key, way),
        counterparty_key=counterparty_key,
        direction=way,
        category=label.final_value,
        source_label_id=label.label_id,
        created_by=by,
        created_at=at,
    )


def _unused() -> None:  # keeps `field` importable for dataclass defaults in adapters
    _ = field
