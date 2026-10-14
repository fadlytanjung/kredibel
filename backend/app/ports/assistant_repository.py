"""AssistantRepository port (spec 011, US-011-1)."""

from __future__ import annotations

from typing import Protocol

from app.domain.models.assistant import AssistantMessage, Memory, Thread


class AssistantRepository(Protocol):
    """Stores conversation threads and messages for the Finance Assistant."""

    async def list_threads(self, org_id: str, limit: int = 50) -> list[Thread]:
        """List threads for an org, newest first."""
        ...

    async def get_thread(self, org_id: str, thread_id: str) -> Thread | None:
        """Get a single thread by ID."""
        ...

    async def create_thread(self, org_id: str, thread: Thread) -> Thread:
        """Create a new thread."""
        ...

    async def list_messages(self, org_id: str, thread_id: str) -> list[AssistantMessage]:
        """List messages in a thread, oldest first."""
        ...

    async def append_message(
        self, org_id: str, thread_id: str, message: AssistantMessage
    ) -> AssistantMessage:
        """Append a message to a thread."""
        ...

    async def list_memories(self, org_id: str, uid: str) -> list[Memory]:
        """List remembered user preferences."""
        ...

    async def forget_memories(self, org_id: str, uid: str) -> None:
        """Forget all remembered user preferences."""
        ...

    async def forget_memory(self, org_id: str, uid: str, memory_id: str) -> None:
        """Forget a specific remembered user preference."""
        ...

    async def save_memory(self, org_id: str, uid: str, memory: Memory) -> Memory:
        """Save a remembered user preference."""
        ...

