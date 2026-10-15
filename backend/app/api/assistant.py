"""Assistant API routes (spec 011; contracts/openapi.yaml /api/assistant/*)."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.models.assistant import AssistantMessage, Thread


class ThreadCreateBody(BaseModel):
    scope: str = "WORKSPACE"
    title: str | None = Field(default=None, max_length=100)


class AskRequestBody(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


def _thread_body(t: Thread) -> dict[str, Any]:
    return {
        "threadId": t.thread_id,
        "title": t.title,
        "scope": t.scope,
        "createdAt": t.created_at.isoformat() if t.created_at else None,
        "lastMessageAt": t.last_message_at.isoformat() if t.last_message_at else None,
    }


def _message_body(m: AssistantMessage) -> dict[str, Any]:
    answer_dict: dict[str, Any] | None = None
    if m.answer is not None:
        answer_dict = {
            "parts": [p.model_dump() for p in m.answer.parts],
            "citations": [c.model_dump() for c in m.answer.citations],
            "grounding": m.answer.grounding.model_dump() if m.answer.grounding else None,
            "toolsUsed": m.answer.tools_used,
        }
    return {
        "messageId": m.message_id,
        "role": m.role,
        "question": m.question,
        "answer": answer_dict,
        "createdAt": m.created_at.isoformat(),
    }


def create_assistant_router(deps: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["assistant"])

    @router.get("/assistant/threads")
    async def list_threads(
        limit: int = 50,
        cursor: str | None = None,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        threads, next_cursor = await deps.assistant_service.list_threads(
            org_id, limit=limit, cursor=cursor
        )
        return {
            "items": [_thread_body(t) for t in threads],
            "nextCursor": next_cursor,
        }

    @router.post("/assistant/threads", status_code=status.HTTP_201_CREATED)
    async def create_thread(
        body: ThreadCreateBody,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        thread = await deps.assistant_service.create_thread(
            org_id, title=body.title, scope=body.scope
        )
        return _thread_body(thread)

    @router.get("/assistant/threads/{thread_id}/messages")
    async def list_messages(
        thread_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        thread = await deps.assistant_service.get_thread(org_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
        messages = await deps.assistant_service.list_messages(org_id, thread_id)
        return {"items": [_message_body(m) for m in messages]}

    @router.post("/assistant/threads/{thread_id}/messages")
    async def ask_question(
        thread_id: str,
        body: AskRequestBody,
        request: Request,
        principal: Principal = Depends(workspace_dep),
    ) -> Any:
        org_id = org_of(principal)
        thread = await deps.assistant_service.get_thread(org_id, thread_id)
        if thread is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

        accept = request.headers.get("accept", "")
        if "text/event-stream" in accept:
            async def event_generator():
                try:
                    async for event in deps.assistant_service.stream_ask(
                        org_id=org_id,
                        uid=principal.uid,
                        thread_id=thread_id,
                        question=body.question,
                    ):
                        yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                except Exception as exc:
                    yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'status': 'error'})}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        msg = await deps.assistant_service.ask(
            org_id=org_id,
            uid=principal.uid,
            thread_id=thread_id,
            question=body.question,
        )
        return _message_body(msg)


    @router.get("/bank-lines/{tx_id}/ai-suggestion")
    async def get_match_ai_suggestion(
        tx_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        suggestion = await deps.assistant_service.suggest_reconciliation_match(org_id, tx_id)
        return {
            "recommendedDocId": suggestion.recommended_doc_id,
            "confidence": suggestion.confidence,
            "reason": suggestion.reason,
            "missingDocumentAdvice": suggestion.missing_document_advice,
        }

    @router.get("/assistant/memories")
    async def list_memories(
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        memories = await deps.assistant_service.list_memories(org_id, principal.uid)
        return {
            "items": [
                {
                    "memoryId": m.memory_id,
                    "fact": m.fact,
                    "updatedAt": m.updated_at.isoformat() if m.updated_at else None,
                }
                for m in memories
            ]
        }

    @router.delete("/assistant/memories", status_code=status.HTTP_204_NO_CONTENT)
    async def forget_memories(
        principal: Principal = Depends(workspace_dep),
    ) -> None:
        org_id = org_of(principal)
        await deps.assistant_service.forget_memories(org_id, principal.uid)

    @router.delete("/assistant/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def forget_memory(
        memory_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> None:
        org_id = org_of(principal)
        await deps.assistant_service.forget_memory(org_id, principal.uid, memory_id)

    return router

