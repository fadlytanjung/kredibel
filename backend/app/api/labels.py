"""Labels and learning (docs/10 §2.10; spec 016, AC-016-5…7)."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.labels import Label


class LabelDecisionBody(BaseModel):
    action: Literal["CONFIRM", "CORRECT"]
    value: str | None = None
    note: str | None = Field(default=None, max_length=500)
    apply_to_similar: bool = Field(default=False, alias="applyToSimilar")

    model_config = {"populate_by_name": True}


class BulkConfirmBody(BaseModel):
    label_ids: list[str] = Field(alias="labelIds", min_length=1, max_length=200)

    model_config = {"populate_by_name": True}


def label_body(lb: Label) -> dict[str, Any]:
    s = lb.subject
    return {
        "labelId": lb.label_id,
        "task": lb.task,
        "subject": {
            "display": s.display,
            **({"docId": s.doc_id} if s.doc_id else {}),
            **({"pageNo": s.page_no} if s.page_no else {}),
            **({"field": s.field} if s.field else {}),
            **({"txId": s.tx_id} if s.tx_id else {}),
            **({"counterpartyId": s.counterparty_id} if s.counterparty_id else {}),
        },
        "month": lb.month,
        "ai": {
            "value": lb.ai.value,
            "confidence": float(lb.ai.confidence) if lb.ai.confidence is not None else None,
            "source": lb.ai.source,
            "model": lb.ai.model,
            "promptVersion": lb.ai.prompt_version,
            "runId": lb.ai.run_id,
            "traceId": lb.ai.trace_id,
            "spanId": lb.ai.span_id,
            "ruleId": lb.ai.rule_id,
            "at": lb.ai.at.isoformat(),
        },
        "final": {"value": lb.final_value, "source": lb.final_source},
        "status": lb.status,
        "needsCheck": lb.needs_check,
        "framework": lb.framework,
        "cashflowClass": lb.cashflow_class,
        "decidedBy": lb.decided_by,
        "decidedAt": lb.decided_at.isoformat() if lb.decided_at else None,
        "note": lb.note,
        "aiDisagreesWithPerson": lb.ai_disagrees_with_person,
        "extractionUrl": lb.extraction_url,
        "pageImageUrl": lb.page_image_url,
        "dataset": {"use": lb.dataset_use, "reason": lb.dataset_reason},
    }


def create_labels_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/labels", tags=["labels"])

    @router.get("")
    async def list_labels(
        task: str | None = Query(
            default=None, pattern="^(DOC_TYPE|PAGE_TYPE|CATEGORY|COUNTERPARTY_ROLE|FIELD_VALUE)$"
        ),
        status: str | None = Query(default=None, pattern="^(AI_PROPOSED|VERIFIED|CORRECTED)$"),
        needs_check: bool | None = Query(default=None, alias="needsCheck"),
        doc_id: str | None = Query(default=None, alias="docId"),
        month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
        dataset_use: str | None = Query(
            default=None, alias="datasetUse", pattern="^(TRAIN|EVAL|EXCLUDED)$"
        ),
        sort: str = Query(default="confidence", pattern="^(confidence|newest)$"),
        limit: int = Query(default=50, ge=1, le=200),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        items, summary = await provider.label_service.list_labels(
            org_of(principal),
            task=task,
            status=status,
            needs_check=needs_check,
            doc_id=doc_id,
            month=month,
            dataset_use=dataset_use,
            sort=sort,
            limit=limit,
        )
        return {"items": [label_body(lb) for lb in items], "nextCursor": None, "summary": summary}

    @router.post("/sync")
    async def sync_labels(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        """Create the labels the stored books imply (spec 016); people's decisions stay."""
        return {"created": await provider.label_service.sync_all(principal)}

    @router.post("/bulk-confirm")
    async def bulk_confirm(
        body: BulkConfirmBody, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        updated = await provider.label_service.bulk_confirm(principal, body.label_ids)
        return {"updated": updated}

    @router.get("/{label_id}")
    async def get_label(
        label_id: str, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        return label_body(await provider.label_service.get(org_of(principal), label_id))

    @router.post("/{label_id}/decision")
    async def decide_label(
        label_id: str, body: LabelDecisionBody, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        decided = await provider.label_service.decide(
            principal,
            label_id,
            action=body.action,
            value=body.value,
            note=body.note,
            apply_to_similar=body.apply_to_similar,
        )
        return label_body(decided)

    return router
