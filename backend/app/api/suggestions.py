"""Profile suggestions (docs/10 §2.7; spec 014, AC-014-5, AC-014-7)."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.profile_suggestions import Suggestion


class SuggestionDecisionBody(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]


def suggestion_body(s: Suggestion) -> dict[str, Any]:
    return {
        "suggestionId": s.suggestion_id,
        "field": s.field,
        "value": dict(s.value),
        "display": s.display,
        "confidence": s.confidence,
        "basis": s.basis,
        "evidence": list(s.evidence),
        "status": s.status,
        "conflictWith": s.conflict_with,
    }


def create_suggestions_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/suggestions", tags=["insight"])

    @router.get("")
    async def list_suggestions(
        status: str | None = Query(default=None, pattern="^(PENDING|CONFLICT|ACCEPTED|REJECTED)$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        found = await provider.suggestion_service.list_suggestions(org_of(principal), status=status)
        return {"items": [suggestion_body(s) for s in found]}

    @router.patch("/{suggestion_id}")
    async def decide_suggestion(
        suggestion_id: str,
        body: SuggestionDecisionBody,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        decided = await provider.suggestion_service.decide(
            principal, org_of(principal), suggestion_id, body.decision
        )
        return suggestion_body(decided)

    return router
