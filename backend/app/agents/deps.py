"""Dependencies passed to workflow node factories and stages (docs/06 §2.2)."""

from dataclasses import dataclass

from app.core.clock import Clock, SystemClock
from app.core.settings import Settings
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.month_repository import MonthRepository
from app.ports.run_repository import RunRepository
from app.ports.task_queue import TaskQueue


@dataclass
class PipelineDeps:
    """All external dependencies, models and repositories required by workflow nodes."""

    settings: Settings
    run_repo: RunRepository
    doc_repo: DocumentRepository
    month_repo: MonthRepository
    storage: DocumentStorage | None = None
    task_queue: TaskQueue | None = None
    clock: Clock = SystemClock()
