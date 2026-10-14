"""In-memory fake for AssistantRepository."""

from __future__ import annotations

from app.domain.models.assistant import AssistantMessage, Memory, Thread
from app.ports.assistant_repository import AssistantRepository


class FakeAssistantRepository(AssistantRepository):
    def __init__(self) -> None:
        self.threads: dict[tuple[str, str], Thread] = {}
        self.messages: dict[tuple[str, str], list[AssistantMessage]] = {}
        self.memories: dict[tuple[str, str], list[Memory]] = {}

    async def list_threads(self, org_id: str, limit: int = 50) -> list[Thread]:
        found = [t for (o, _), t in self.threads.items() if o == org_id]
        found.sort(key=lambda t: t.created_at or 0, reverse=True)
        return found[:limit]

    async def get_thread(self, org_id: str, thread_id: str) -> Thread | None:
        return self.threads.get((org_id, thread_id))

    async def create_thread(self, org_id: str, thread: Thread) -> Thread:
        self.threads[(org_id, thread.thread_id)] = thread
        self.messages.setdefault((org_id, thread.thread_id), [])
        return thread

    async def list_messages(self, org_id: str, thread_id: str) -> list[AssistantMessage]:
        return list(self.messages.get((org_id, thread_id), []))

    async def append_message(
        self, org_id: str, thread_id: str, message: AssistantMessage
    ) -> AssistantMessage:
        msg_list = self.messages.setdefault((org_id, thread_id), [])
        msg_list.append(message)
        thread = self.threads.get((org_id, thread_id))
        if thread is not None:
            thread.last_message_at = message.created_at
        return message

    async def list_memories(self, org_id: str, uid: str) -> list[Memory]:
        return list(self.memories.get((org_id, uid), []))

    async def forget_memories(self, org_id: str, uid: str) -> None:
        self.memories[(org_id, uid)] = []

    async def forget_memory(self, org_id: str, uid: str, memory_id: str) -> None:
        current = self.memories.get((org_id, uid), [])
        self.memories[(org_id, uid)] = [m for m in current if m.memory_id != memory_id]

    async def save_memory(self, org_id: str, uid: str, memory: Memory) -> Memory:
        current = self.memories.setdefault((org_id, uid), [])
        current.append(memory)
        return memory

