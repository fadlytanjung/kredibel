"""Integration tests for Documents API routes and workspace isolation (spec 003).

Normative references:
- AC-003-1, AC-003-2, AC-003-5, AC-003-7, AC-003-10, AC-003-11
- contracts/openapi.yaml /api/documents endpoints
"""

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.core.settings import Settings
from app.domain.models.workspace import Subscription
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.unit.test_auth import FakeTokenVerifier

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"
NOW = datetime(2026, 10, 11, 8, 0, tzinfo=UTC)


def _minimal_pdf() -> bytes:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    pdf.new_page(width=200, height=200)
    out = io.BytesIO()
    pdf.save(out)
    pdf.close()
    return out.getvalue()


class ApiHarness:
    def __init__(self) -> None:
        self.workspaces = FakeWorkspaceRepository()
        self.usage = FakeUsageRepository(workspaces=self.workspaces)
        self.usage.subscriptions["org_1"] = Subscription(
            plan_id="free_trial",
            status="ACTIVE",
            trial_ends_at=datetime(2026, 10, 25, 0, 0, tzinfo=UTC),
        )
        self.usage.subscriptions["org_2"] = Subscription(
            plan_id="free_trial",
            status="ACTIVE",
            trial_ends_at=datetime(2026, 10, 25, 0, 0, tzinfo=UTC),
        )
        self.identity = FakeIdentityAdmin()
        self.doc_repo = FakeDocumentRepository()
        self.storage = FakeDocumentStorage()
        self.task_queue = FakeTaskQueue()
        self.clock = FixedClock(NOW)
        self.tokens = FakeTokenVerifier(
            {
                "ws1_user": {
                    "uid": "u-1",
                    "email": "user1@example.test",
                    "orgId": "org_1",
                    "role": "owner",
                },
                "ws2_user": {
                    "uid": "u-2",
                    "email": "user2@example.test",
                    "orgId": "org_2",
                    "role": "owner",
                },
                "no_ws_user": {"uid": "u-3", "email": "user3@example.test"},
            }
        )
        settings = Settings(app_role="web")  # type: ignore[arg-type]
        self.deps = AppDeps(
            settings,
            load_plans(PLANS_FILE),
            workspace_repo=self.workspaces,
            usage_repo=self.usage,
            identity=self.identity,
            doc_repo=self.doc_repo,
            storage=self.storage,
            task_queue=self.task_queue,
            renderer=DefaultPageRenderer(),
            spreadsheet_reader=DefaultSpreadsheetReader(),
            clock=self.clock,
            token_verifier=self.tokens,
        )
        self.app = create_app(settings, deps=self.deps)

    def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def harness() -> ApiHarness:
    return ApiHarness()


@pytest.mark.asyncio
async def test_upload_and_get_document(harness: ApiHarness) -> None:
    pdf_bytes = _minimal_pdf()
    async with harness.client() as c:
        # 1. Upload document (POST /api/documents)
        res = await c.post(
            "/api/documents",
            files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
            data={"docTypeHint": "BANK_STATEMENT"},
            headers=harness.auth("ws1_user"),
        )
        assert res.status_code == 201, res.text
        doc = res.json()
        assert doc["fileName"] == "statement.pdf"
        assert doc["contentType"] == "application/pdf"
        assert doc["docType"] == "BANK_STATEMENT"
        assert doc["status"] == "UPLOADED"
        assert doc["pageCount"] == 1
        doc_id = doc["docId"]

        # 2. Get document detail (GET /api/documents/{docId})
        res_get = await c.get(f"/api/documents/{doc_id}", headers=harness.auth("ws1_user"))
        assert res_get.status_code == 200
        get_doc = res_get.json()
        assert get_doc["docId"] == doc_id
        assert get_doc["fileName"] == "statement.pdf"


@pytest.mark.asyncio
async def test_workspace_isolation_foreign_doc_returns_404(harness: ApiHarness) -> None:
    pdf_bytes = _minimal_pdf()
    async with harness.client() as c:
        # User in org_1 uploads
        res = await c.post(
            "/api/documents",
            files={"file": ("org1_doc.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        assert res.status_code == 201
        doc_id = res.json()["docId"]

        # User in org_2 attempts GET /api/documents/{docId} -> 404 (AC-003-11)
        res_foreign = await c.get(f"/api/documents/{doc_id}", headers=harness.auth("ws2_user"))
        assert res_foreign.status_code == 404

        # User in org_2 attempts GET /api/documents/{docId}/file -> 404 (AC-003-11)
        res_foreign_file = await c.get(
            f"/api/documents/{doc_id}/file", headers=harness.auth("ws2_user")
        )
        assert res_foreign_file.status_code == 404

        # User in org_2 attempts GET /api/documents/{docId}/pages/1 -> 404 (AC-003-11)
        res_foreign_page = await c.get(
            f"/api/documents/{doc_id}/pages/1", headers=harness.auth("ws2_user")
        )
        assert res_foreign_page.status_code == 404

        # User in org_2 attempts DELETE /api/documents/{docId} -> 404 (AC-003-11)
        res_foreign_del = await c.delete(
            f"/api/documents/{doc_id}", headers=harness.auth("ws2_user")
        )
        assert res_foreign_del.status_code == 404

        # Org 2 document list does not contain org 1 document
        res_list = await c.get("/api/documents", headers=harness.auth("ws2_user"))
        assert res_list.status_code == 200
        assert len(res_list.json()["items"]) == 0


@pytest.mark.asyncio
async def test_list_documents_and_duplicate_upload(harness: ApiHarness) -> None:
    pdf_bytes = _minimal_pdf()
    async with harness.client() as c:
        # First upload -> original
        res1 = await c.post(
            "/api/documents",
            files={"file": ("statement1.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        assert res1.status_code == 201
        orig_id = res1.json()["docId"]

        # Second upload of same file -> duplicate (AC-003-5)
        res2 = await c.post(
            "/api/documents",
            files={"file": ("statement2.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        assert res2.status_code == 201
        dup = res2.json()
        assert dup["status"] == "DUPLICATE"
        assert dup["duplicate"]["kind"] == "EXACT"
        assert dup["duplicate"]["ofDocId"] == orig_id
        dup_id = dup["docId"]

        # List all documents
        res_list = await c.get("/api/documents", headers=harness.auth("ws1_user"))
        assert res_list.status_code == 200
        items = res_list.json()["items"]
        assert len(items) == 2

        # Filter by duplicate=true
        res_dup_list = await c.get(
            "/api/documents?duplicate=true", headers=harness.auth("ws1_user")
        )
        assert res_dup_list.status_code == 200
        dup_items = res_dup_list.json()["items"]
        assert len(dup_items) == 1
        assert dup_items[0]["docId"] == dup_id


@pytest.mark.asyncio
async def test_get_file_and_page_rendering(harness: ApiHarness) -> None:
    pdf_bytes = _minimal_pdf()
    async with harness.client() as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        doc_id = res.json()["docId"]

        # Original file stream
        res_file = await c.get(f"/api/documents/{doc_id}/file", headers=harness.auth("ws1_user"))
        assert res_file.status_code == 200
        assert res_file.headers["content-type"].startswith("application/pdf")
        assert res_file.content == pdf_bytes

        # Rendered full page PNG
        res_page = await c.get(
            f"/api/documents/{doc_id}/pages/1?variant=full", headers=harness.auth("ws1_user")
        )
        assert res_page.status_code == 200
        assert res_page.headers["content-type"].startswith("image/png")
        assert len(res_page.content) > 0

        # Thumbnail PNG
        res_thumb = await c.get(
            f"/api/documents/{doc_id}/pages/1?variant=thumb", headers=harness.auth("ws1_user")
        )
        assert res_thumb.status_code == 200
        assert res_thumb.headers["content-type"].startswith("image/png")
        assert len(res_thumb.content) > 0

        # Invalid page returns 404
        res_bad_page = await c.get(
            f"/api/documents/{doc_id}/pages/99", headers=harness.auth("ws1_user")
        )
        assert res_bad_page.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_and_cascade(harness: ApiHarness) -> None:
    pdf_bytes = _minimal_pdf()
    async with harness.client() as c:
        res1 = await c.post(
            "/api/documents",
            files={"file": ("original.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        orig_id = res1.json()["docId"]

        res2 = await c.post(
            "/api/documents",
            files={"file": ("copy.pdf", pdf_bytes, "application/pdf")},
            headers=harness.auth("ws1_user"),
        )
        dup_id = res2.json()["docId"]

        # Delete original document (DELETE /api/documents/{docId})
        res_del = await c.delete(f"/api/documents/{orig_id}", headers=harness.auth("ws1_user"))
        assert res_del.status_code == 204

        # Original is gone (404)
        res_get_orig = await c.get(f"/api/documents/{orig_id}", headers=harness.auth("ws1_user"))
        assert res_get_orig.status_code == 404

        # Duplicate is also gone due to cascade (original-of-duplicate rule, AC-003-10)
        res_get_dup = await c.get(f"/api/documents/{dup_id}", headers=harness.auth("ws1_user"))
        assert res_get_dup.status_code == 404
