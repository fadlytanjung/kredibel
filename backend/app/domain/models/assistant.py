"""Domain models for the Finance Assistant (spec 011) and AI reconciliation matching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class Thread:
    thread_id: str
    title: str
    scope: str = "WORKSPACE"
    created_at: datetime | None = None
    last_message_at: datetime | None = None


class AnswerPart(BaseModel):
    type: Literal["text", "table", "chart"] = "text"
    text: str | None = None
    columns: list[str] | None = None
    rows: list[list[str]] | None = None
    chart: (
        Literal["MONEY_FLOW", "MONTHLY_IN_OUT", "CATEGORY_BREAKDOWN", "INVOICE_BREAKDOWN"] | None
    ) = None
    query: dict[str, Any] | None = None


class CitationRef(BaseModel):
    ref: str
    label: str = ""


class GroundingRef(BaseModel):
    verdict: Literal["AGREED", "TEMPLATE", "REJECTED"] = "AGREED"
    citations: list[str] = Field(default_factory=list)


class MessageAnswer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    parts: list[AnswerPart] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)
    grounding: GroundingRef | None = None
    tools_used: list[str] = Field(
        default_factory=list,
        serialization_alias="toolsUsed",
        validation_alias="toolsUsed",
    )


@dataclass
class AssistantMessage:
    message_id: str
    role: Literal["user", "assistant"]
    created_at: datetime
    question: str | None = None
    answer: MessageAnswer | None = None


class MatchSuggestion(BaseModel):
    recommended_doc_id: str | None = None
    confidence: float = 0.0
    reason: str = ""
    missing_document_advice: str = ""


@dataclass
class Memory:
    memory_id: str
    fact: str
    updated_at: datetime | None = None

