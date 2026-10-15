"""Firestore models for Assistant threads and messages."""

from datetime import datetime
from typing import Any

from app.adapters.firestore.models.base import FirestoreModel


class ThreadDoc(FirestoreModel):
    thread_id: str
    title: str
    scope: str = "WORKSPACE"
    created_at: datetime
    last_message_at: datetime | None = None


class AssistantMessageDoc(FirestoreModel):
    message_id: str
    role: str
    question: str | None = None
    answer: dict[str, Any] | None = None
    created_at: datetime


class AssistantMemoryDoc(FirestoreModel):
    memory_id: str
    fact: str
    updated_at: datetime

