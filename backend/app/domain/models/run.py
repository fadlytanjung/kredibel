"""Domain models for Run and RunStage (docs/09 §3.15).

Normative references: docs/09 §3.15, docs/06 §1-§4, contracts/openapi.yaml.
Pure domain logic: no framework dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class RunKind(StrEnum):
    DOCUMENT = "DOCUMENT"
    MONTH = "MONTH"


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class StageStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class RunStage:
    node: str
    parent: str | None = None
    status: StageStatus = StageStatus.QUEUED
    started_at: datetime | None = None
    ended_at: datetime | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    summary: str | None = None
    trace_span_id: str | None = None


@dataclass
class Run:
    run_id: str
    kind: RunKind
    target: str  # docId or yyyy-mm
    status: RunStatus = RunStatus.QUEUED
    stages: list[RunStage] = field(default_factory=list)
    trace_id: str | None = None
    models: list[str] = field(default_factory=list)
    prompt_versions: dict[str, str] = field(default_factory=dict)
    labels: dict[str, int] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    policy_hashes: dict[str, str] = field(default_factory=dict)
    generation: int | None = None
    created_at: datetime | None = None
    ended_at: datetime | None = None
