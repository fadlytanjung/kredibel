from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import AsyncClient, Query

from app.adapters.firestore.models.assistant import (
    AssistantMemoryDoc,
    AssistantMessageDoc,
    ThreadDoc,
)
from app.adapters.firestore.txn import dump
from app.domain.models.assistant import (
    AssistantMessage,
    Memory,
    MessageAnswer,
    Thread,
)
from app.ports.assistant_repository import AssistantRepository


def _thread_to_doc(t: Thread) -> ThreadDoc:
    return ThreadDoc(
        thread_id=t.thread_id,
        title=t.title,
        scope=t.scope,
        created_at=t.created_at or datetime.now(UTC),
        last_message_at=t.last_message_at,
    )


def _thread_to_domain(d: ThreadDoc) -> Thread:
    return Thread(
        thread_id=d.thread_id,
        title=d.title,
        scope=d.scope,
        created_at=d.created_at,
        last_message_at=d.last_message_at,
    )


def _msg_to_doc(m: AssistantMessage) -> AssistantMessageDoc:
    answer_dict: dict[str, Any] | None = None
    if m.answer is not None:
        answer_dict = m.answer.model_dump(by_alias=True)
    return AssistantMessageDoc(
        message_id=m.message_id,
        role=m.role,
        question=m.question,
        answer=answer_dict,
        created_at=m.created_at,
    )


def _msg_to_domain(d: AssistantMessageDoc) -> AssistantMessage:
    answer_obj = None
    if d.answer:
        answer_obj = MessageAnswer.model_validate(d.answer)
    return AssistantMessage(
        message_id=d.message_id,
        role=d.role,  # type: ignore[arg-type]
        question=d.question,
        answer=answer_obj,
        created_at=d.created_at or datetime.now(UTC),
    )


class FirestoreAssistantRepository(AssistantRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _threads_col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("assistantThreads")

    async def list_threads(self, org_id: str, limit: int = 50) -> list[Thread]:
        query = (
            self._threads_col(org_id)
            .order_by("createdAt", direction=Query.DESCENDING)
            .limit(limit)
        )
        snaps = [s async for s in query.stream()]
        return [_thread_to_domain(ThreadDoc.model_validate(s.to_dict())) for s in snaps if s.exists]

    async def get_thread(self, org_id: str, thread_id: str) -> Thread | None:
        snap = await self._threads_col(org_id).document(thread_id).get()
        return _thread_to_domain(ThreadDoc.model_validate(snap.to_dict())) if snap.exists else None

    async def create_thread(self, org_id: str, thread: Thread) -> Thread:
        doc = _thread_to_doc(thread)
        await self._threads_col(org_id).document(thread.thread_id).set(dump(doc))
        return thread

    async def list_messages(self, org_id: str, thread_id: str) -> list[AssistantMessage]:
        col = self._threads_col(org_id).document(thread_id).collection("messages")
        query = col.order_by("createdAt", direction=Query.ASCENDING).limit(100)
        snaps = [s async for s in query.stream()]
        return [
            _msg_to_domain(AssistantMessageDoc.model_validate(s.to_dict()))
            for s in snaps
            if s.exists
        ]

    async def append_message(
        self, org_id: str, thread_id: str, message: AssistantMessage
    ) -> AssistantMessage:
        thread_ref = self._threads_col(org_id).document(thread_id)
        msg_doc = _msg_to_doc(message)
        batch = self._db.batch()
        batch.set(thread_ref.collection("messages").document(message.message_id), dump(msg_doc))
        batch.update(thread_ref, {"lastMessageAt": message.created_at})
        await batch.commit()
        return message

    def _memories_col(self, org_id: str, uid: str):
        return (
            self._db.collection("orgs")
            .document(org_id)
            .collection("users")
            .document(uid)
            .collection("assistantMemories")
        )

    async def list_memories(self, org_id: str, uid: str) -> list[Memory]:
        snaps = [s async for s in self._memories_col(org_id, uid).stream()]
        return [
            Memory(
                memory_id=s.to_dict().get("memory_id") or s.id,
                fact=s.to_dict().get("fact", ""),
                updated_at=s.to_dict().get("updated_at"),
            )
            for s in snaps
            if s.exists
        ]

    async def forget_memories(self, org_id: str, uid: str) -> None:
        snaps = [s async for s in self._memories_col(org_id, uid).stream()]
        batch = self._db.batch()
        for s in snaps:
            batch.delete(s.reference)
        await batch.commit()

    async def forget_memory(self, org_id: str, uid: str, memory_id: str) -> None:
        await self._memories_col(org_id, uid).document(memory_id).delete()

    async def save_memory(self, org_id: str, uid: str, memory: Memory) -> Memory:
        doc = AssistantMemoryDoc(
            memory_id=memory.memory_id,
            fact=memory.fact,
            updated_at=memory.updated_at or datetime.now(UTC),
        )
        await self._memories_col(org_id, uid).document(memory.memory_id).set(dump(doc))
        return memory

