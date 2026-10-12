"""Dependencies passed to workflow node factories and stages (docs/06 §2.2)."""

from dataclasses import dataclass

from app.core.clock import Clock, SystemClock
from app.core.settings import Settings
from app.domain.checks.policy import ForensicsPolicy
from app.domain.models.invoice import Invoice, Receipt
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_reader import DocumentReader
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.file_inspector import FileInspector
from app.ports.finding_repository import FindingRepository
from app.ports.month_repository import MonthRepository
from app.ports.page_text import PageText
from app.ports.record_repository import DocumentRecords
from app.ports.run_repository import RunRepository
from app.ports.task_queue import TaskQueue
from app.ports.workspace_repository import WorkspaceRepository


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
    # Reading (spec 005, ADR-023); without them the reading nodes pass the document through.
    reader: DocumentReader | None = None
    page_text: PageText | None = None
    bank_lines: BankLineRepository | None = None
    invoices: DocumentRecords[Invoice] | None = None
    receipts: DocumentRecords[Receipt] | None = None
    # The workspace's own names decide sales or purchase (AC-005-1).
    workspaces: WorkspaceRepository | None = None
    # Checks (spec 006): the file's structure, the policy, and where findings go.
    inspector: FileInspector | None = None
    forensics: ForensicsPolicy | None = None
    findings: FindingRepository | None = None
