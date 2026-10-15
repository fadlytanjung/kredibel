"""LabelRepository on Firestore (docs/09 §3.19, §3.20)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.label import LabelDoc, WorkspaceRuleDoc
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.labels import AiDecision, Label, LabelSubject, WorkspaceRule, merge
from app.domain.models.events import AuditEvent
from app.ports.label_repository import LabelRepository


def _to_doc(lb: Label) -> LabelDoc:
    subject = {
        "display": lb.subject.display,
        **({"docId": lb.subject.doc_id} if lb.subject.doc_id else {}),
        **({"pageNo": lb.subject.page_no} if lb.subject.page_no else {}),
        **({"field": lb.subject.field} if lb.subject.field else {}),
        **({"txId": lb.subject.tx_id} if lb.subject.tx_id else {}),
        **({"counterpartyId": lb.subject.counterparty_id} if lb.subject.counterparty_id else {}),
    }
    ai: dict[str, Any] = {
        "value": lb.ai.value,
        "source": lb.ai.source,
        "at": lb.ai.at,
        "confidence": str(lb.ai.confidence) if lb.ai.confidence is not None else None,
        "model": lb.ai.model,
        "promptVersion": lb.ai.prompt_version,
        "runId": lb.ai.run_id,
        "traceId": lb.ai.trace_id,
        "spanId": lb.ai.span_id,
        "ruleId": lb.ai.rule_id,
    }
    return LabelDoc(
        label_id=lb.label_id,
        task=lb.task,
        subject=subject,
        month=lb.month,
        ai=ai,
        final={"value": lb.final_value, "source": lb.final_source},
        status=lb.status,
        needs_check=lb.needs_check,
        framework=lb.framework,
        cashflow_class=lb.cashflow_class,
        decided_by=lb.decided_by,
        decided_at=lb.decided_at,
        note=lb.note,
        ai_disagrees_with_person=lb.ai_disagrees_with_person,
        dataset={"use": lb.dataset_use, "reason": lb.dataset_reason},
        extraction_url=lb.extraction_url,
        page_image_url=lb.page_image_url,
    )


def _to_domain(d: LabelDoc) -> Label:
    s, ai = d.subject, d.ai
    conf = ai.get("confidence")
    at = ai.get("at")
    return Label(
        label_id=d.label_id,
        task=cast(Any, d.task),
        subject=LabelSubject(
            display=str(s.get("display") or ""),
            doc_id=s.get("docId"),
            page_no=int(s["pageNo"]) if s.get("pageNo") else None,
            field=s.get("field"),
            tx_id=s.get("txId"),
            counterparty_id=s.get("counterpartyId"),
        ),
        ai=AiDecision(
            value=str(ai.get("value") or ""),
            source=cast(Any, ai.get("source") or "MODEL"),
            at=at if isinstance(at, datetime) else datetime.fromisoformat(str(at)),
            confidence=Decimal(str(conf)) if conf is not None else None,
            model=ai.get("model"),
            prompt_version=ai.get("promptVersion"),
            run_id=ai.get("runId"),
            trace_id=ai.get("traceId"),
            span_id=ai.get("spanId"),
            rule_id=ai.get("ruleId"),
        ),
        final_value=str(d.final.get("value") or ""),
        final_source=cast(Any, d.final.get("source") or "MODEL"),
        status=cast(Any, d.status),
        needs_check=d.needs_check,
        month=d.month,
        framework=d.framework,
        cashflow_class=d.cashflow_class,
        decided_by=d.decided_by,
        decided_at=d.decided_at,
        note=d.note,
        ai_disagrees_with_person=d.ai_disagrees_with_person,
        dataset_use=cast(Any, d.dataset.get("use") or "EXCLUDED"),
        dataset_reason=d.dataset.get("reason"),
        extraction_url=d.extraction_url,
        page_image_url=d.page_image_url,
    )


def _confidence(label: Label) -> float:
    return float(label.ai.confidence) if label.ai.confidence is not None else -1.0


class FirestoreLabelRepository(LabelRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("labels")

    def _rules(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("workspaceRules")

    async def upsert(self, org_id: str, labels: list[Label]) -> list[Label]:
        out: list[Label] = []
        batch = self._db.batch()
        for fresh in labels:
            snap = await self._col(org_id).document(fresh.label_id).get()
            existing = _to_domain(LabelDoc.model_validate(snap.to_dict())) if snap.exists else None
            stored = merge(existing, fresh)
            batch.set(self._col(org_id).document(stored.label_id), dump(_to_doc(stored)))
            out.append(stored)
        if labels:
            await batch.commit()
        return out

    async def get(self, org_id: str, label_id: str) -> Label | None:
        snap = await self._col(org_id).document(label_id).get()
        return _to_domain(LabelDoc.model_validate(snap.to_dict())) if snap.exists else None

    async def list_labels(
        self,
        org_id: str,
        *,
        task: str | None = None,
        status: str | None = None,
        needs_check: bool | None = None,
        doc_id: str | None = None,
        month: str | None = None,
        dataset_use: str | None = None,
        run_id: str | None = None,
        sort: str = "confidence",
        limit: int | None = 50,
    ) -> list[Label]:
        query: Any = self._col(org_id)
        if task:
            query = query.where(filter=FieldFilter("task", "==", task))
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        if needs_check is not None:
            query = query.where(filter=FieldFilter("needsCheck", "==", needs_check))
        if doc_id:
            query = query.where(filter=FieldFilter("subject.docId", "==", doc_id))
        if month:
            query = query.where(filter=FieldFilter("month", "==", month))
        if dataset_use:
            query = query.where(filter=FieldFilter("dataset.use", "==", dataset_use))
        if run_id:
            query = query.where(filter=FieldFilter("ai.runId", "==", run_id))
        found = [_to_domain(LabelDoc.model_validate(s.to_dict())) async for s in query.stream()]
        if sort == "newest":
            found.sort(key=lambda lb: (lb.decided_at or lb.ai.at).isoformat(), reverse=True)
        else:
            found.sort(key=lambda lb: (not lb.needs_check, _confidence(lb), lb.label_id))
        return found if limit is None else found[:limit]

    async def decide(self, org_id: str, label: Label, event: AuditEvent) -> None:
        batch = self._db.batch()
        batch.set(self._col(org_id).document(label.label_id), dump(_to_doc(label)))
        batch.set(
            self._db.collection("orgs")
            .document(org_id)
            .collection("events")
            .document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def save_rule(self, org_id: str, rule: WorkspaceRule) -> None:
        await (
            self._rules(org_id)
            .document(rule.rule_id)
            .set(
                dump(
                    WorkspaceRuleDoc(
                        rule_id=rule.rule_id,
                        counterparty_key=rule.counterparty_key,
                        direction=rule.direction,
                        category=rule.category,
                        source_label_id=rule.source_label_id,
                        created_by=rule.created_by,
                        created_at=rule.created_at,
                        active=rule.active,
                    )
                )
            )
        )

    async def list_rules(self, org_id: str) -> list[WorkspaceRule]:
        out = []
        async for snap in (
            self._rules(org_id).where(filter=FieldFilter("active", "==", True)).stream()
        ):
            d = WorkspaceRuleDoc.model_validate(snap.to_dict())
            out.append(
                WorkspaceRule(
                    rule_id=d.rule_id,
                    counterparty_key=d.counterparty_key,
                    direction=cast(Any, d.direction),
                    category=d.category,
                    source_label_id=d.source_label_id,
                    created_by=d.created_by,
                    created_at=d.created_at,
                    active=d.active,
                )
            )
        return out
