"""Local development: an upload runs the document workflow in-process (docs/13 §7, docs/16 §1).

Before this, the inline queue only recorded tasks and every local upload stayed UPLOADED forever.
"""

import io
from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient

from app.adapters.cloud_tasks import InlineTaskQueue
from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.core.settings import Settings
from app.domain.models.document import DocStatus
from app.domain.models.workspace import Subscription
from app.domain.reading import DocClassification
from app.main import AppDeps, create_app
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.clock import FixedClock
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.integration.test_documents_api import PLANS_FILE, _minimal_pdf
from tests.unit.test_auth import FakeTokenVerifier

AUTH = {"Authorization": "Bearer owner"}


def _deps(classification: DocClassification | None = None) -> AppDeps:
    workspaces = FakeWorkspaceRepository()
    usage = FakeUsageRepository(workspaces=workspaces)
    usage.subscriptions["org_1"] = Subscription(
        plan_id="free_trial", status="TRIALING", trial_ends_at=datetime(2026, 10, 25, tzinfo=UTC)
    )
    settings = Settings(app_role="all", task_queue_mode="inline")  # type: ignore[arg-type]
    return AppDeps(
        settings,
        load_plans(PLANS_FILE),
        workspace_repo=workspaces,
        usage_repo=usage,
        identity=FakeIdentityAdmin(),
        run_repo=FakeRunRepository(),
        month_repo=FakeMonthRepository(),
        doc_repo=FakeDocumentRepository(),
        storage=FakeDocumentStorage(),
        renderer=DefaultPageRenderer(),
        spreadsheet_reader=DefaultSpreadsheetReader(),
        clock=FixedClock(datetime(2026, 10, 11, 8, 0, tzinfo=UTC)),
        reader=FakeDocumentReader(classification),
        bank_lines=FakeBankLineRepository(),
        token_verifier=FakeTokenVerifier(
            {"owner": {"uid": "u-1", "email": "o@example.test", "orgId": "org_1", "role": "owner"}}
        ),
    )


async def _upload(deps: AppDeps, **data: str) -> str:
    app = create_app(deps.settings, deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("statement.pdf", io.BytesIO(_minimal_pdf()), "application/pdf")},
            data=data,
            headers=AUTH,
        )
    assert res.status_code == 201, res.text
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()
    return res.json()["docId"]


async def test_an_upload_the_reader_cannot_place_asks_for_the_type():
    deps = _deps(DocClassification(doc_type="OTHER", confidence=0.4))
    doc_id = await _upload(deps)
    doc = await deps.doc_repo.get_document("org_1", doc_id)
    assert doc is not None and doc.status == DocStatus.NEEDS_INPUT
    runs = await deps.run_repo.list_runs("org_1")
    assert [r.status.value for r in runs] == ["DONE"]


async def test_an_upload_with_a_type_runs_the_whole_workflow():
    deps = _deps()
    doc_id = await _upload(deps, docTypeHint="BANK_STATEMENT")
    doc = await deps.doc_repo.get_document("org_1", doc_id)
    assert doc is not None and doc.status == DocStatus.DONE
