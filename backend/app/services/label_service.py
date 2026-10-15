"""Labels: what people check and correct (spec 016, AC-016-5…7)."""

import contextlib
from dataclasses import replace
from decimal import Decimal
from typing import Any, Literal

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.categorize import CategoryPolicy
from app.domain.counterparties import ROLE_ORDER, fold_name
from app.domain.errors import (
    ForbiddenError,
    NotFoundError,
    ValidationProblem,
    WorkspaceRequiredError,
)
from app.domain.labels import Label, LearningPolicy, decide, rule_for, summarize
from app.domain.models.document import DocStatus, DocType
from app.domain.models.events import AuditEvent
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_repository import DocumentRepository
from app.ports.label_repository import LabelRepository
from app.ports.task_queue import TaskQueue
from app.services.bank_line_service import BankLineService
from app.services.month_service import MonthService

Action = Literal["CONFIRM", "CORRECT"]
_CAN_DECIDE = ("owner", "accountant", "reviewer")
BULK_LIMIT = 200


def _org(principal: Principal) -> str:
    if principal.org_id is None:
        raise WorkspaceRequiredError()
    return principal.org_id


class LabelService:
    def __init__(
        self,
        *,
        labels: LabelRepository,
        policy: LearningPolicy,
        categories: CategoryPolicy,
        clock: Clock,
        bank_lines: BankLineService | None = None,
        lines: BankLineRepository | None = None,
        documents: DocumentRepository | None = None,
        months: MonthService | None = None,
        task_queue: TaskQueue | None = None,
    ) -> None:
        self._labels = labels
        self._policy = policy
        self._categories = categories
        self._clock = clock
        self._bank_lines = bank_lines
        self._lines = lines
        self._documents = documents
        self._months = months
        self._task_queue = task_queue

    async def list_labels(self, org_id: str, **filters: Any) -> tuple[list[Label], dict[str, Any]]:
        """The filtered page and the summary over every label of the workspace (AC-016-5)."""
        items = await self._labels.list_labels(org_id, **filters)
        summary = summarize(await self._labels.list_labels(org_id, limit=None))
        return items, summary

    async def for_run(self, org_id: str, run_id: str) -> list[Label]:
        """The labels a run proposed (spec 017: the run's counts and its events' join)."""
        return await self._labels.list_labels(org_id, run_id=run_id, limit=None)

    async def get(self, org_id: str, label_id: str) -> Label:
        label = await self._labels.get(org_id, label_id)
        if label is None:
            raise NotFoundError(f"Label {label_id} not found")
        return label

    async def decide(
        self,
        principal: Principal,
        label_id: str,
        *,
        action: Action,
        value: str | None = None,
        note: str | None = None,
        apply_to_similar: bool = False,
    ) -> Label:
        """AC-016-6: VERIFIED or CORRECTED by a person, with its event; a CATEGORY or DOC_TYPE
        decision is applied to the line or document and marks its months dirty; AC-016-7: a
        category decision can be remembered for the party and direction."""
        org_id = _org(principal)
        if principal.role not in _CAN_DECIDE:
            raise ForbiddenError("Viewers cannot confirm or correct labels.")
        label = await self.get(org_id, label_id)
        if action == "CORRECT":
            self._check_value(label, value)
        try:
            decided = decide(
                label,
                action=action,
                by=principal.uid,
                at=self._clock.now(),
                policy=self._policy,
                value=value,
                note=note,
            )
        except ValueError as exc:
            raise ValidationProblem("value", str(exc)) from exc
        event = AuditEvent(
            event_id=new_id("evt"),
            type="LABEL_VERIFIED" if decided.status == "VERIFIED" else "LABEL_CORRECTED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=decided.decided_at or self._clock.now(),
            subject={
                "labelId": label.label_id,
                "task": label.task,
                **({"docId": label.subject.doc_id} if label.subject.doc_id else {}),
                **({"txId": label.subject.tx_id} if label.subject.tx_id else {}),
            },
            details={
                "aiValue": label.ai.value,
                "value": decided.final_value,
                **({"note": decided.note} if decided.note else {}),
                **({"applyToSimilar": True} if apply_to_similar else {}),
            },
        )
        await self._labels.decide(org_id, decided, event)
        await self._apply(principal, decided, apply_to_similar=apply_to_similar)
        return decided

    async def bulk_confirm(self, principal: Principal, label_ids: list[str]) -> int:
        """Confirm up to 200 labels as the AI proposed them; decided ones are left as they are."""
        if len(label_ids) > BULK_LIMIT:
            raise ValidationProblem("labelIds", f"At most {BULK_LIMIT} labels at once.")
        if principal.role not in _CAN_DECIDE:
            raise ForbiddenError("Viewers cannot confirm or correct labels.")
        org_id = _org(principal)
        count = 0
        for label_id in dict.fromkeys(label_ids):
            label = await self._labels.get(org_id, label_id)
            if label is None or label.status != "AI_PROPOSED":
                continue
            await self.decide(principal, label_id, action="CONFIRM")
            count += 1
        return count

    def _check_value(self, label: Label, value: str | None) -> None:
        if not value or not value.strip():
            raise ValidationProblem("value", "A correction needs a value.")
        chosen = value.strip()
        if label.task == "CATEGORY" and chosen not in self._categories.categories:
            raise ValidationProblem("value", "Choose a category from the policy.")
        if label.task == "DOC_TYPE" and chosen not in {t.value for t in DocType} - {"UNKNOWN"}:
            raise ValidationProblem("value", "Choose a document type.")
        if label.task == "COUNTERPARTY_ROLE" and chosen not in ROLE_ORDER:
            raise ValidationProblem("value", "Choose a counterparty role.")

    async def _apply(self, principal: Principal, label: Label, *, apply_to_similar: bool) -> None:
        org_id = _org(principal)
        if label.task == "CATEGORY" and label.subject.tx_id:
            if self._bank_lines is not None:
                # The line may be gone; the label keeps the person's decision either way.
                with contextlib.suppress(NotFoundError):
                    await self._bank_lines.set_category(
                        principal, label.subject.tx_id, label.final_value
                    )
            if apply_to_similar and self._lines is not None:
                line = await self._lines.get_line(org_id, label.subject.tx_id)
                key = (
                    (
                        line.counterparty_id
                        or (fold_name(line.counterparty_name) if line.counterparty_name else "")
                    )
                    if line is not None
                    else ""
                )
                if line is not None and key:
                    rule = rule_for(
                        label,
                        counterparty_key=key,
                        direction="in" if line.amount > 0 else "out",
                        by=principal.uid,
                        at=self._clock.now(),
                    )
                    await self._labels.save_rule(org_id, rule)
        elif label.task == "DOC_TYPE" and label.subject.doc_id and self._documents is not None:
            doc = await self._documents.get_document(org_id, label.subject.doc_id)
            if doc is None:
                return
            if label.status == "CORRECTED" and label.final_value != doc.doc_type.value:
                await self._documents.save_document(
                    org_id,
                    replace(
                        doc,
                        doc_type=DocType(label.final_value),
                        type_confidence=Decimal("1"),
                        type_set_by=principal.uid,
                        status=DocStatus.READING,
                        status_detail=None,
                    ),
                )
                if self._task_queue is not None:
                    await self._task_queue.enqueue_document_task(org_id, doc.doc_id, new_id("run"))
                if self._months is not None and doc.months:
                    await self._months.mark_dirty(org_id, list(doc.months), reason="label_decided")
            else:
                await self._documents.save_document(org_id, replace(doc, type_set_by=principal.uid))
