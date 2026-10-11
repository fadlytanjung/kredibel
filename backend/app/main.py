"""Composition root: builds the dependencies and mounts routers by role.

Normative references: docs/13 §1 and §2.2 (composition root + DI), spec 001 AC-001-1, AC-001-10.
"""

from collections.abc import Callable
from typing import Any, TypeVar, cast

from fastapi import FastAPI
from google.cloud.firestore import AsyncClient

from app.adapters.cloud_tasks import CloudTasksQueue, InlineTaskQueue
from app.adapters.firebase_identity import FirebaseIdentityAdmin
from app.adapters.firestore.document_repo import FirestoreDocumentRepository
from app.adapters.firestore.usage_repo import FirestoreUsageRepository
from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.adapters.gcs_storage import GcsDocumentStorage
from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.api.bank_accounts import create_bank_accounts_router
from app.api.documents import create_documents_router
from app.api.health import create_health_router
from app.api.me import create_me_router
from app.api.plans import create_plans_router
from app.api.static import mount_static_spa
from app.api.tasks import create_tasks_router
from app.api.workspace import create_workspace_router
from app.core.auth import (
    FirebaseTokenVerifier,
    TokenVerifier,
    get_principal_dependency,
    require_workspace,
)
from app.core.clock import Clock, SystemClock
from app.core.errors import register_error_handlers
from app.core.logging import LoggingMiddleware, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.settings import Settings
from app.domain.plans import PlanCatalog
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.identity_admin import IdentityAdmin
from app.ports.page_renderer import PageRenderer
from app.ports.spreadsheet_reader import SpreadsheetReader
from app.ports.task_queue import TaskQueue
from app.ports.workspace_repository import UsageRepository, WorkspaceRepository
from app.services.document_service import DocumentService
from app.services.entitlement_service import EntitlementService
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
            "firestore", lambda: AsyncClient(project=self.settings.google_cloud_project)
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
            lambda: self._storage
            or GcsDocumentStorage(
                self.settings.google_cloud_project, self.settings.docs_bucket
            ),
        )

    @property
    def task_queue(self) -> TaskQueue:
        return self._once(
            "task_queue",
            lambda: self._task_queue
            or (
                CloudTasksQueue(
                    project_id=self.settings.google_cloud_project,
                    location=self.settings.tasks_location,
                    document_queue=self.settings.tasks_queue_documents,
                    month_queue=self.settings.tasks_queue_months,
                    invoker_service_account=self.settings.tasks_invoker_sa,
                )
                if self.settings.task_queue_mode == "cloud"
                else InlineTaskQueue()
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
                clock=self.clock,
            ),
        )


def create_app(
    settings: Settings | None = None,
    deps: AppDeps | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance with role-based routing."""
    active_settings = settings or Settings()

    setup_logging(
        log_level=active_settings.log_level,
        service=active_settings.service_name,
        version=active_settings.app_version,
    )

    if deps is None:
        # AC-013-5: an invalid plan catalog stops the process before it serves anything.
        plans = load_plans(active_settings.contract_path(active_settings.plans_file))
        deps = AppDeps(active_settings, plans, token_verifier=token_verifier)

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

    # 1. Health check (every role)
    app.include_router(create_health_router(active_settings))

    # 2. Web role endpoints
    if active_settings.app_role in ("web", "all"):
        app.include_router(create_me_router(deps, principal_dep))
        app.include_router(create_plans_router(deps, principal_dep))
        app.include_router(create_workspace_router(deps, principal_dep, workspace_dep))
        app.include_router(create_bank_accounts_router(deps, workspace_dep))
        app.include_router(create_documents_router(deps, workspace_dep))

    # 3. Worker role endpoints
    if active_settings.app_role in ("worker", "all"):
        app.include_router(create_tasks_router())

    # 4. The SPA catch-all matches every path, so it must be registered after every router.
    if active_settings.app_role in ("web", "all"):
        mount_static_spa(app, static_dir=active_settings.static_dir)

    return app


# Default app instance for ASGI servers (Uvicorn)
app = create_app()
