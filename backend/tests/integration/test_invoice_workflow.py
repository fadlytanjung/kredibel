"""Invoices end to end without a model (spec 005, T005-03): upload → parse → classify → read →
ground → invoice records → API. The reading is recorded from the synthetic invoice, printed as the
invoice prints it; sales or purchase comes from the workspace's own name, not the classifier."""

import io
from datetime import UTC, datetime
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.adapters.cloud_tasks import InlineTaskQueue
from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.core.settings import Settings
from app.domain.models.document import DocStatus
from app.domain.models.workspace import Profile, Subscription
from app.domain.reading import DocClassification, InvoiceLineReading, InvoicePageReading
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.ledger_repository import FakeLedgerRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.record_repository import fake_invoices
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository, demo_workspace
from tests.integration.test_documents_api import PLANS_FILE
from tests.unit.test_auth import FakeTokenVerifier

PDF = Path(__file__).resolve().parents[1] / "fixtures" / "invoices" / "scr-sales-2026-03.pdf"
AUTH = {"Authorization": "Bearer owner"}


def _recorded(page: int) -> InvoicePageReading:
    return InvoicePageReading(
        page=page,
        invoice_number="INV/SCR/2026/03/0009",
        issuer_name="Sunrise Coffee Roasters",
        issuer_tax_id="99-731.204.5-018.000",
        buyer_name="Daybreak Café",
        buyer_tax_id="99-208.551.9-423.000",
        issue_date_text="12 Mar 2026",
        due_date_text="26 Mar 2026",
        currency="IDR",
        payment_bank_text="Archipelago Commerce Bank",
        payment_account_text="9900004821",
        lines=[
            InvoiceLineReading(
                description="Drip bags, box of 20",
                quantity_text="93",
                unit_price_text="95,000.00",
                amount_text="8,835,000.00",
            ),
            InvoiceLineReading(
                description="Robusta roasted beans, 1 kg",
                quantity_text="49",
                unit_price_text="180,000.00",
                amount_text="8,820,000.00",
            ),
        ],
        subtotal_text="17,655,000.00",
        tax_text="1,942,050.00",
        total_text="19,597,050.00",
        supply_kind="GOODS",
    )


def _deps():
    workspaces = FakeWorkspaceRepository()
    workspaces.workspaces["org_1"] = demo_workspace("org_1").model_copy(
        update={
            "name": "Sunrise Coffee Roasters",
            "profile": Profile(legal_name="Sunrise Coffee Roasters"),
        }
    )
    usage = FakeUsageRepository(workspaces=workspaces)
    usage.subscriptions["org_1"] = Subscription(
        plan_id="free_trial", status="TRIALING", trial_ends_at=datetime(2026, 10, 25, tzinfo=UTC)
    )
    settings = Settings(app_role="all", task_queue_mode="inline", month_run_delay_seconds=0)  # type: ignore[arg-type]
    reader = FakeDocumentReader(
        DocClassification(doc_type="PURCHASE_INVOICE", confidence=0.93), invoice_pages=_recorded
    )
    invoices = fake_invoices()
    deps = AppDeps(
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
        clock=FixedClock(datetime(2026, 4, 2, tzinfo=UTC)),
        reader=reader,
        invoices=invoices,
        ledger=FakeLedgerRepository(),
        token_verifier=FakeTokenVerifier(
            {"owner": {"uid": "u-1", "orgId": "org_1", "role": "owner"}}
        ),
    )
    return deps, invoices


def _client(deps) -> AsyncClient:
    app = create_app(deps.settings, deps=deps)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _upload(client: AsyncClient, deps) -> str:
    files = {"file": ("invoice.pdf", io.BytesIO(PDF.read_bytes()), "application/pdf")}
    res = await client.post("/api/documents", files=files, headers=AUTH)
    assert res.status_code == 201, res.text
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()
    return res.json()["docId"]


async def test_an_invoice_upload_ends_with_a_grounded_sales_invoice():
    deps, invoices = _deps()
    async with _client(deps) as client:
        doc_id = await _upload(client, deps)
        doc = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()
        listed = (await client.get("/api/invoices", params={"docId": doc_id}, headers=AUTH)).json()

    assert doc["status"] == DocStatus.DONE.value, doc.get("statusDetail")
    assert doc["months"] == ["2026-03"]
    assert doc["reading"]["agreement"] == "1.000"
    assert doc["reading"]["lines"] == 1
    [inv] = listed["items"]
    assert inv["kind"] == "SALES"  # the workspace issued it, whatever the classifier said
    assert doc["docType"] == "SALES_INVOICE"  # and the document's type follows (AC-005-1)
    assert (inv["number"], inv["issueDate"], inv["dueDate"]) == (
        "INV/SCR/2026/03/0009",
        "2026-03-12",
        "2026-03-26",
    )
    assert inv["total"] == {"amount": "19597050.00", "currency": "IDR"}
    assert inv["tax"] == {"amount": "1942050.00", "currency": "IDR"}
    assert [ln["amount"]["amount"] for ln in inv["lines"]] == ["8835000.00", "8820000.00"]
    assert inv["lines"][0]["qty"] == "93"
    assert inv["payToMasked"] == "••••4821"
    assert inv["issuerTaxIdMasked"] == "••••.000"
    assert "9900004821" not in str(inv)
    assert {r["status"] for r in inv["readings"].values()} == {"AGREED"}
    assert inv["readings"]["total"]["bbox"] is not None
    assert inv["notes"] == []


async def test_removing_the_invoice_document_removes_its_invoices():
    deps, invoices = _deps()
    async with _client(deps) as client:
        doc_id = await _upload(client, deps)
        assert await invoices.list_records("org_1", doc_id=doc_id)
        assert (await client.delete(f"/api/documents/{doc_id}", headers=AUTH)).status_code == 204
    assert await invoices.list_records("org_1", doc_id=doc_id) == []


async def test_the_buyers_workspace_files_the_same_invoice_as_a_purchase():
    """The classifier calls it a sales invoice; the workspace is the buyer, so the code decides
    PURCHASE and the document's type follows (AC-005-1): the library's purchase filter finds it."""
    deps, _ = _deps()
    workspace = deps.workspace_repo.workspaces["org_1"]  # type: ignore[attr-defined]
    deps.workspace_repo.workspaces["org_1"] = workspace.model_copy(  # type: ignore[attr-defined]
        update={"name": "Daybreak Café", "profile": Profile(legal_name="Daybreak Café")}
    )
    deps._reader = FakeDocumentReader(  # the classifier guesses "sales"
        DocClassification(doc_type="SALES_INVOICE", confidence=0.93), invoice_pages=_recorded
    )
    async with _client(deps) as client:
        doc_id = await _upload(client, deps)
        doc = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()
        [inv] = (await client.get("/api/invoices", params={"docId": doc_id}, headers=AUTH)).json()[
            "items"
        ]

    assert inv["kind"] == "PURCHASE"
    assert doc["docType"] == "PURCHASE_INVOICE"
