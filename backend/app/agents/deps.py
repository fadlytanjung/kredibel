"""Dependencies passed to workflow node factories and stages (docs/06 §2.2)."""

from dataclasses import dataclass

from app.core.clock import Clock, SystemClock
from app.core.settings import Settings
from app.domain.categorize import CategoryPolicy
from app.domain.checks.policy import ForensicsPolicy
from app.domain.labels import LearningPolicy
from app.domain.models.invoice import Invoice, Receipt
from app.domain.reconciliation_policy import ReconciliationPolicy
from app.domain.risk import RiskPolicy
from app.ports.bank_line_repository import BankLineRepository
from app.ports.chunk_repository import ChunkRepository
from app.ports.counterparty_repository import CounterpartyRepository
from app.ports.decision_repository import DecisionRepository
from app.ports.document_reader import DocumentReader
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.embedder import Embedder
from app.ports.file_inspector import FileInspector
from app.ports.finding_repository import FindingRepository
from app.ports.label_repository import LabelRepository
from app.ports.ledger_repository import LedgerRepository
from app.ports.match_repository import MatchRepository
from app.ports.month_repository import MonthRepository
from app.ports.page_text import PageText
from app.ports.record_repository import DocumentRecords
from app.ports.review_item_repository import ReviewItemRepository
from app.ports.run_repository import RunRepository
from app.ports.suggestion_repository import SuggestionRepository
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
    categories: CategoryPolicy | None = None
    # Month reconciliation (spec 007, ADR-025).
    matches: MatchRepository | None = None
    decisions: DecisionRepository | None = None
    reconciliation: ReconciliationPolicy | None = None
    # Risk policy (spec 008).
    risk_policy: RiskPolicy | None = None
    # Review queue (spec 009).
    review_items: ReviewItemRepository | None = None
    # Ledger repository (spec 018).
    ledger: LedgerRepository | None = None
    # Clients and suppliers, profile suggestions (spec 014).
    counterparties: CounterpartyRepository | None = None
    suggestions: SuggestionRepository | None = None
    # Labels and learning (spec 016): where every automatic decision goes, and the thresholds.
    labels: LabelRepository | None = None
    learning: LearningPolicy | None = None
    embedder: Embedder | None = None  # verified examples in prompts (AC-016-9)
    # The extraction store (spec 022): each read page's chunks.
    chunks: ChunkRepository | None = None
