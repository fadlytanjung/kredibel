"""Composition root: builds the dependencies and mounts routers by role.

Normative references: docs/13 §1 and §2.2 (composition root + DI), spec 001 AC-001-1, AC-001-10.
"""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from fastapi import FastAPI
from google.cloud.firestore import AsyncClient

from app.adapters.cloud_tasks import CloudTasksQueue, InlineTaskQueue
from app.adapters.firebase_identity import FirebaseIdentityAdmin
from app.adapters.firestore.bank_line_repo import FirestoreBankLineRepository
from app.adapters.firestore.decision_repo import FirestoreDecisionRepository
from app.adapters.firestore.document_repo import FirestoreDocumentRepository
from app.adapters.firestore.finding_repo import FirestoreFindingRepository
from app.adapters.firestore.match_repo import FirestoreMatchRepository
from app.adapters.firestore.month_repo import FirestoreMonthRepository
from app.adapters.firestore.record_repo import firestore_invoices, firestore_receipts
from app.adapters.firestore.run_repo import FirestoreRunRepository
from app.adapters.firestore.usage_repo import FirestoreUsageRepository
from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.adapters.gcs_storage import GcsDocumentStorage
from app.adapters.gemini_reader import GeminiDocumentReader
from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.pdf_inspector import PdfInspector
from app.adapters.policy_files import (
    load_category_policy,
    load_forensics,
    load_plans,
    load_reconciliation_policy,
)
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.adapters.text_layer import PdfTextLayer
from app.agents.deps import PipelineDeps
from app.agents.runtime import run_workflow
from app.agents.workflows.document_workflow import build_document_workflow
from app.agents.workflows.month_workflow import build_month_workflow
from app.api.bank_accounts import create_bank_accounts_router
from app.api.bank_lines import create_bank_lines_router
from app.api.decisions import create_decisions_router
from app.api.documents import create_documents_router
from app.api.findings import create_findings_router
from app.api.health import create_health_router
from app.api.matches import create_matches_router
from app.api.me import create_me_router
from app.api.months import create_months_router
from app.api.plans import create_plans_router
from app.api.records import create_records_router
from app.api.runs import create_runs_router
from app.api.static import mount_static_spa
from app.api.tasks import create_tasks_router
from app.api.workspace import create_workspace_router
from app.core.auth import (
    FirebaseTokenVerifier,
    GoogleOidcTokenVerifier,
    NoopTaskTokenVerifier,
    TaskTokenVerifier,
    TokenVerifier,
    get_principal_dependency,
    get_task_auth_dependency,
    require_workspace,
)
from app.core.clock import Clock, SystemClock
from app.core.errors import register_error_handlers
from app.core.logging import LoggingMiddleware, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.settings import Settings
from app.domain.categorize import CategoryPolicy
from app.domain.checks.policy import ForensicsPolicy
from app.domain.models.invoice import Invoice, Receipt
from app.domain.plans import PlanCatalog
from app.domain.reconciliation_policy import ReconciliationPolicy
from app.observability.tracing import setup_tracing
from app.ports.bank_line_repository import BankLineRepository
from app.ports.decision_repository import DecisionRepository
from app.ports.document_reader import DocumentReader
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.file_inspector import FileInspector
from app.ports.finding_repository import FindingRepository
from app.ports.identity_admin import IdentityAdmin
from app.ports.match_repository import MatchRepository
from app.ports.month_repository import MonthRepository
from app.ports.page_renderer import PageRenderer
from app.ports.page_text import PageText
from app.ports.record_repository import DocumentRecords
from app.ports.run_repository import RunRepository
from app.ports.spreadsheet_reader import SpreadsheetReader
from app.ports.task_queue import TaskQueue
from app.ports.workspace_repository import UsageRepository, WorkspaceRepository
from app.services.bank_line_service import BankLineService
from app.services.decision_service import DecisionService
from app.services.document_service import DocumentService
from app.services.entitlement_service import EntitlementService
from app.services.month_service import MonthService
from app.services.record_service import RecordService
from app.services.runs import DocumentWorkflowRunner, MonthWorkflowRunner, RunService
from app.services.workspace_service import WorkspaceService

T = TypeVar("T")


class AppDeps:
    """Every dependency, built on first use; tests pass fakes for the ones they need.

    Lazy so that start-up and tests that never touch Firestore need no Google credentials.
    """

    def __init__(
        self,
        settings: Settings,
        plans: PlanCatalog,
        *,
        workspace_repo: WorkspaceRepository | None = None,
        usage_repo: UsageRepository | None = None,
        identity: IdentityAdmin | None = None,
        clock: Clock | None = None,
        token_verifier: TokenVerifier | None = None,
        doc_repo: DocumentRepository | None = None,
        storage: DocumentStorage | None = None,
        task_queue: TaskQueue | None = None,
        renderer: PageRenderer | None = None,
        spreadsheet_reader: SpreadsheetReader | None = None,
        run_repo: RunRepository | None = None,
        month_repo: MonthRepository | None = None,
        task_token_verifier: TaskTokenVerifier | None = None,
        document_workflow_runner: DocumentWorkflowRunner | None = None,
        reader: DocumentReader | None = None,
        page_text: PageText | None = None,
        bank_lines: BankLineRepository | None = None,
        invoices: DocumentRecords[Invoice] | None = None,
        receipts: DocumentRecords[Receipt] | None = None,
        findings: FindingRepository | None = None,
        decisions: DecisionRepository | None = None,
        matches: MatchRepository | None = None,
    ) -> None:
        self.settings = settings
        self._plans = plans
        self._workspace_repo = workspace_repo
        self._usage_repo = usage_repo
        self._identity = identity
        self._clock = clock
        self._token_verifier = token_verifier
        self._doc_repo = doc_repo
        self._storage = storage
        self._task_queue = task_queue
        self._renderer = renderer
        self._spreadsheet_reader = spreadsheet_reader
        self._run_repo = run_repo
        self._month_repo = month_repo
        self._task_token_verifier = task_token_verifier
        self._document_workflow_runner = document_workflow_runner
        self._reader = reader
        self._page_text = page_text
        self._bank_lines = bank_lines
        self._invoices = invoices
        self._receipts = receipts
        self._findings = findings
        self._decisions = decisions
        self._matches = matches
        self._built: dict[str, Any] = {}

    def _once(self, name: str, build: Callable[[], T]) -> T:
        if name not in self._built:
            self._built[name] = build()
        return cast(T, self._built[name])

    @property
    def plans(self) -> PlanCatalog:
        return self._plans

    @property
    def clock(self) -> Clock:
        return self._once("clock", lambda: self._clock or SystemClock())

    @property
    def token_verifier(self) -> TokenVerifier:
        return self._once("token_verifier", lambda: self._token_verifier or FirebaseTokenVerifier())

    @property
    def firestore(self) -> AsyncClient:
        # Honours FIRESTORE_EMULATOR_HOST for local runs.
        return self._once(
            "firestore",
            lambda: AsyncClient(
                project=self.settings.google_cloud_project,
                database=self.settings.firestore_database,
            ),
        )

    @property
    def workspace_repo(self) -> WorkspaceRepository:
        return self._once(
            "workspace_repo",
            lambda: self._workspace_repo or FirestoreWorkspaceRepository(self.firestore),
        )

    @property
    def usage_repo(self) -> UsageRepository:
        return self._once(
            "usage_repo", lambda: self._usage_repo or FirestoreUsageRepository(self.firestore)
        )

    @property
    def identity(self) -> IdentityAdmin:
        return self._once("identity", lambda: self._identity or FirebaseIdentityAdmin())

    @property
    def doc_repo(self) -> DocumentRepository:
        return self._once(
            "doc_repo",
            lambda: self._doc_repo or FirestoreDocumentRepository(self.firestore),
        )

    @property
    def storage(self) -> DocumentStorage:
        return self._once(
            "storage",
            lambda: (
                self._storage
                or GcsDocumentStorage(self.settings.google_cloud_project, self.settings.docs_bucket)
            ),
        )

    def _inline_queue(self) -> InlineTaskQueue:
        """Local development: the worker runs in-process (docs/13 §7). A web-only process just
        records tasks, as nothing in it serves /tasks."""
        if self.settings.app_role not in ("all", "worker"):
            return InlineTaskQueue()

        async def on_document(org_id: str, doc_id: str, run_id: str, attempt: int) -> None:
            await self.run_service.process_document_task(
                org_id=org_id, doc_id=doc_id, run_id=run_id, attempt=attempt
            )

        async def on_month(org_id: str, month: str, generation: int, run_id: str) -> None:
            await self.run_service.reconcile_month_task(
                org_id=org_id, month=month, generation=generation, run_id=run_id
            )

        return InlineTaskQueue(on_document=on_document, on_month=on_month)

    @property
    def task_queue(self) -> TaskQueue:
        return self._once(
            "task_queue",
            lambda: (
                self._task_queue
                or (
                    CloudTasksQueue(
                        project_id=self.settings.google_cloud_project,
                        location=self.settings.tasks_location,
                        document_queue=self.settings.tasks_queue_documents,
                        month_queue=self.settings.tasks_queue_months,
                        invoker_service_account=self.settings.tasks_invoker_sa,
                        worker_base_url=self.settings.worker_url,
                    )
                    if self.settings.task_queue_mode == "cloud"
                    else self._inline_queue()
                )
            ),
        )

    @property
    def renderer(self) -> PageRenderer:
        return self._once("renderer", lambda: self._renderer or DefaultPageRenderer())

    @property
    def spreadsheet_reader(self) -> SpreadsheetReader:
        return self._once(
            "spreadsheet_reader",
            lambda: self._spreadsheet_reader or DefaultSpreadsheetReader(),
        )

    @property
    def workspace_service(self) -> WorkspaceService:
        return self._once(
            "workspace_service",
            lambda: WorkspaceService(
                repo=self.workspace_repo,
                identity=self.identity,
                plans=self.plans,
                clock=self.clock,
                signup_mode=self.settings.signup_mode,
                max_workspaces=self.settings.max_workspaces,
            ),
        )

    @property
    def entitlement_service(self) -> EntitlementService:
        return self._once(
            "entitlement_service",
            lambda: EntitlementService(
                repo=self.usage_repo,
                plans=self.plans,
                clock=self.clock,
                run_quota_per_org_per_day=self.settings.run_quota_per_org_per_day,
            ),
        )

    @property
    def document_service(self) -> DocumentService:
        return self._once(
            "document_service",
            lambda: DocumentService(
                doc_repo=self.doc_repo,
                storage=self.storage,
                task_queue=self.task_queue,
                entitlements=self.entitlement_service,
                renderer=self.renderer,
                spreadsheet_reader=self.spreadsheet_reader,
                bank_lines=self.bank_lines,
                invoices=self.invoices,
                receipts=self.receipts,
                clock=self.clock,
                runs_enabled=self.settings.runs_enabled,
            ),
        )

    @property
    def task_token_verifier(self) -> TaskTokenVerifier:
        return self._once(
            "task_token_verifier",
            lambda: (
                self._task_token_verifier
                or (
                    GoogleOidcTokenVerifier(expected_email=self.settings.tasks_invoker_sa)
                    if self.settings.task_queue_mode == "cloud"
                    else NoopTaskTokenVerifier()
                )
            ),
        )

    @property
    def reader(self) -> DocumentReader:
        return self._once("reader", lambda: self._reader or GeminiDocumentReader(self.settings))

    @property
    def page_text(self) -> PageText:
        return self._once("page_text", lambda: self._page_text or PdfTextLayer())

    @property
    def findings(self) -> FindingRepository:
        return self._once(
            "findings", lambda: self._findings or FirestoreFindingRepository(self.firestore)
        )

    @property
    def decisions(self) -> DecisionRepository:
        return self._once(
            "decisions", lambda: self._decisions or FirestoreDecisionRepository(self.firestore)
        )

    @property
    def matches(self) -> MatchRepository:
        return self._once(
            "matches", lambda: self._matches or FirestoreMatchRepository(self.firestore)
        )

    @property
    def reconciliation(self) -> ReconciliationPolicy:
        return self._once(
            "reconciliation",
            lambda: load_reconciliation_policy(
                self.settings.contract_path(self.settings.policy_dir)
            ),
        )

    @property
    def decision_service(self) -> DecisionService:
        return self._once(
            "decision_service",
            lambda: DecisionService(
                decisions=self.decisions,
                doc_repo=self.doc_repo,
                invoices=self.invoices,
                receipts=self.receipts,
                bank_lines=self.bank_lines,
                workspaces=self.workspace_repo,
                month_repo=self.month_repo,
                task_queue=self.task_queue,
                clock=self.clock,
                month_run_delay_seconds=self.settings.month_run_delay_seconds,
            ),
        )

    @property
    def forensics(self) -> ForensicsPolicy:
        return self._once(
            "forensics",
            lambda: load_forensics(self.settings.contract_path(self.settings.policy_dir)),
        )

    @property
    def categories(self) -> CategoryPolicy:
        return self._once(
            "categories",
            lambda: load_category_policy(
                self.settings.contract_path(self.settings.categories_file),
                self.settings.contract_path(self.settings.policy_dir),
            ),
        )

    @property
    def inspector(self) -> FileInspector:
        return self._once("inspector", PdfInspector)

    @property
    def invoices(self) -> DocumentRecords[Invoice]:
        return self._once("invoices", lambda: self._invoices or firestore_invoices(self.firestore))

    @property
    def receipts(self) -> DocumentRecords[Receipt]:
        return self._once("receipts", lambda: self._receipts or firestore_receipts(self.firestore))

    @property
    def bank_lines(self) -> BankLineRepository:
        return self._once(
            "bank_lines", lambda: self._bank_lines or FirestoreBankLineRepository(self.firestore)
        )

    @property
    def run_repo(self) -> RunRepository:
        return self._once(
            "run_repo", lambda: self._run_repo or FirestoreRunRepository(self.firestore)
        )

    @property
    def month_repo(self) -> MonthRepository:
        return self._once(
            "month_repo", lambda: self._month_repo or FirestoreMonthRepository(self.firestore)
        )

    @property
    def document_workflow_runner(self) -> DocumentWorkflowRunner:
        if self._document_workflow_runner is not None:
            return self._document_workflow_runner

        async def _default_runner(org_id: str, doc_id: str, run_id: str, attempt: int) -> None:
            pipeline_deps = PipelineDeps(
                settings=self.settings,
                run_repo=self.run_repo,
                doc_repo=self.doc_repo,
                month_repo=self.month_repo,
                task_queue=self.task_queue,
                clock=self.clock,
                storage=self.storage,
                reader=self.reader,
                page_text=self.page_text,
                bank_lines=self.bank_lines,
                invoices=self.invoices,
                receipts=self.receipts,
                workspaces=self.workspace_repo,
                inspector=self.inspector,
                forensics=self.forensics,
                findings=self.findings,
                categories=self.categories,
            )
            await run_workflow(
                build_document_workflow(pipeline_deps),
                org_id=org_id,
                run_id=run_id,
                node_input={"orgId": org_id, "docId": doc_id, "runId": run_id, "attempt": attempt},
                run_repo=self.run_repo,
                settings=self.settings,
            )

        return _default_runner

    @property
    def month_workflow_runner(self) -> MonthWorkflowRunner:
        async def _default_runner(
            org_id: str, month: str, generation: int, run_id: str
        ) -> dict[str, Any]:
            pipeline_deps = PipelineDeps(
                settings=self.settings,
                run_repo=self.run_repo,
                doc_repo=self.doc_repo,
                month_repo=self.month_repo,
                task_queue=self.task_queue,
                clock=self.clock,
                bank_lines=self.bank_lines,
                invoices=self.invoices,
                receipts=self.receipts,
                workspaces=self.workspace_repo,
                forensics=self.forensics,
                findings=self.findings,
                categories=self.categories,
                matches=self.matches,
                decisions=self.decisions,
                reconciliation=self.reconciliation,
            )
            return await run_workflow(
                build_month_workflow(pipeline_deps),
                org_id=org_id,
                run_id=run_id,
                node_input={
                    "orgId": org_id,
                    "month": month,
                    "generation": generation,
                    "runId": run_id,
                },
                run_repo=self.run_repo,
                settings=self.settings,
            )

        return _default_runner

    @property
    def run_service(self) -> RunService:
        return self._once(
            "run_service",
            lambda: RunService(
                run_repo=self.run_repo,
                month_repo=self.month_repo,
                task_queue=self.task_queue,
                entitlement_service=self.entitlement_service,
                settings=self.settings,
                clock=self.clock,
                document_workflow_runner=self.document_workflow_runner,
                month_workflow_runner=self.month_workflow_runner,
            ),
        )

    @property
    def record_service(self) -> RecordService:
        return self._once(
            "record_service",
            lambda: RecordService(
                invoices=self.invoices, receipts=self.receipts, workspaces=self.workspace_repo
            ),
        )

    @property
    def bank_line_service(self) -> BankLineService:
        return self._once(
            "bank_line_service",
            lambda: BankLineService(
                bank_lines=self.bank_lines,
                workspaces=self.workspace_repo,
                categories=self.categories,
                clock=self.clock,
                months=self.month_service,
            ),
        )

    @property
    def month_service(self) -> MonthService:
        return self._once(
            "month_service",
            lambda: MonthService(
                month_repo=self.month_repo,
                run_service=self.run_service,
            ),
        )


def create_app(
    settings: Settings | None = None,
    deps: AppDeps | None = None,
    token_verifier: TokenVerifier | None = None,
    task_token_verifier: TaskTokenVerifier | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance with role-based routing."""
    active_settings = settings or Settings()

    setup_logging(
        log_level=active_settings.log_level,
        service=active_settings.service_name,
        version=active_settings.app_version,
    )
    setup_tracing(active_settings)

    if deps is None:
        # AC-013-5: an invalid plan catalog stops the process before it serves anything.
        plans = load_plans(active_settings.contract_path(active_settings.plans_file))
        deps = AppDeps(
            active_settings,
            plans,
            token_verifier=token_verifier,
            task_token_verifier=task_token_verifier,
        )

    app = FastAPI(
        title="Kredibel API",
        version=active_settings.app_version,
        docs_url="/docs" if active_settings.app_role != "worker" else None,
        redoc_url=None,
    )
    app.state.plans = deps.plans

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LoggingMiddleware, project_id=active_settings.google_cloud_project)
    register_error_handlers(app)

    principal_dep = get_principal_dependency(verifier=token_verifier or deps.token_verifier)
    workspace_dep = require_workspace(principal_dep)
    task_auth_dep = get_task_auth_dependency(
        verifier=task_token_verifier or deps.task_token_verifier,
        enabled=active_settings.task_queue_mode == "cloud" or task_token_verifier is not None,
    )

    # 1. Health check (every role)
    app.include_router(create_health_router(active_settings))

    # 2. Web role endpoints
    if active_settings.app_role in ("web", "all"):
        app.include_router(create_me_router(deps, principal_dep))
        app.include_router(create_plans_router(deps, principal_dep))
        app.include_router(create_workspace_router(deps, principal_dep, workspace_dep))
        app.include_router(create_bank_accounts_router(deps, workspace_dep))
        app.include_router(create_documents_router(deps, workspace_dep))
        app.include_router(create_runs_router(deps, workspace_dep))
        app.include_router(create_months_router(deps, workspace_dep))
        app.include_router(create_bank_lines_router(deps, workspace_dep))
        app.include_router(create_records_router(deps, workspace_dep))
        app.include_router(create_findings_router(deps, workspace_dep))
        app.include_router(create_decisions_router(deps, workspace_dep))
        app.include_router(create_matches_router(deps, workspace_dep))

    # 3. Worker role endpoints
    if active_settings.app_role in ("worker", "all"):
        app.include_router(create_tasks_router(deps, task_auth_dep=task_auth_dep))

    # 4. The SPA catch-all matches every path, so it must be registered after every router.
    if active_settings.app_role in ("web", "all"):
        mount_static_spa(app, static_dir=active_settings.static_dir)

    return app


# Default app instance for ASGI servers (Uvicorn)
app = create_app()
