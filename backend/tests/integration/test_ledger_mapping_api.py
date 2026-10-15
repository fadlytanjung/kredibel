"""The ledger column confirmation through the API (spec 005, T005-11; AC-005-11, AC-005-12):
GET the proposal with its sample rows, confirm the mapping (edited), and the export is read
again with it. Synthetic data only."""

from datetime import UTC, datetime

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.ledger_parse import compute_layout_signature
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.review_items import confirm_mapping_item
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG, DOC = "org_1", "doc_gl_new"
NOW = datetime(2026, 4, 2, tzinfo=UTC)
INDONESIAN = (
    b"Tanggal;Keterangan;Kode Akun;Nama Akun;Debet;Kredit\n"
    b"02/03/2026;Penjualan kopi;4000;Penjualan;0,00;120.000.000,00\n"
    b"02/03/2026;Penjualan kopi;1110;Bank;120.000.000,00;0,00\n"
    b"03/03/2026;Sewa gudang;6050;Sewa;15.000.000,00;0,00\n"
    b"03/03/2026;Sewa gudang;1110;Bank;0,00;15.000.000,00\n"
    b"15/03/2026;Gaji;6100;Gaji;18.000.000,00;0,00\n"
    b"15/03/2026;Gaji;1110;Bank;0,00;18.000.000,00\n"
)
HEADERS = ["Tanggal", "Keterangan", "Kode Akun", "Nama Akun", "Debet", "Kredit"]
# The proposal deliberately misses the description, as a layout the mapper half-recognizes would.
PROPOSAL = {
    "date": "Tanggal",
    "description": "",
    "accountCode": "Kode Akun",
    "accountName": "Nama Akun",
    "reference": None,
    "debit": "Debet",
    "credit": "Kredit",
    "amount": None,
    "signConvention": None,
    "dateFormat": "DD/MM/YYYY",
    "decimalSeparator": ",",
}


async def _seed(deps) -> str:
    """A ledger export stopped at NEEDS_INPUT by the workflow, with its item."""
    signature = compute_layout_signature(HEADERS)
    doc = Document(
        doc_id=DOC,
        file_name="GL_2026_Q1.csv",
        content_type="text/csv",
        size_bytes=len(INDONESIAN),
        page_count=0,
        sha256="d" * 64,
        gcs_path=f"gs://synthetic/{DOC}.csv",
        uploaded_by="u-1",
        uploaded_at=NOW,
        doc_type=DocType.LEDGER_EXPORT,
        status=DocStatus.NEEDS_INPUT,
        status_detail="Ledger mapping confirmation needed",
        ledger_meta={
            "layoutSignature": signature,
            "mappingStatus": "PROPOSED",
            "mapping": PROPOSAL,
            "header": HEADERS,
        },
    )
    await deps.doc_repo.save_document(ORG, doc)
    await deps.storage.store_original(ORG, DOC, ".csv", INDONESIAN, "text/csv")
    item = confirm_mapping_item(
        DOC,
        "GL_2026_Q1.csv",
        mapping=PROPOSAL,
        header=HEADERS,
        sample_rows=[],
        layout_signature=signature,
    )
    await deps.review_items.upsert_review_item(ORG, item)
    return item.item_id


async def test_ac005_11_the_proposal_is_shown_with_sample_rows_and_confirmed_once_per_layout():
    deps, _ = _deps()
    item_id = await _seed(deps)
    async with _client(deps) as client:
        view = (await client.get(f"/api/documents/{DOC}/ledger-mapping", headers=AUTH)).json()
        assert view["status"] == "PROPOSED" and view["header"] == HEADERS
        assert view["mapping"]["date"] == "Tanggal" and view["mapping"]["description"] == ""
        assert len(view["sampleRows"]) == 5
        assert view["sampleRows"][0]["raw"][0] == "02/03/2026"
        assert view["sampleRows"][0]["parsed"]["credit"]["amount"] == "120000000.00"

        queue = (
            await client.get("/api/review-items", params={"status": "OPEN"}, headers=AUTH)
        ).json()
        [listed] = queue["items"]
        assert listed["kind"] == "CONFIRM_LEDGER_MAPPING" and listed["allowedActions"] == [
            "CONFIRM_MAPPING"
        ]
        assert listed["suggestion"]["mapping"]["mapping"]["accountCode"] == "Kode Akun"

        # A mapping with a column still missing is refused before anything is parsed.
        refused = await client.post(
            f"/api/review-items/{item_id}/resolve",
            json={"action": "CONFIRM_MAPPING", "mapping": PROPOSAL},
            headers=AUTH,
        )
        assert refused.status_code == 422, refused.text
        assert "description: choose the column" in refused.json()["errors"][0]["message"]

        edited = {**PROPOSAL, "description": "Keterangan"}
        res = await client.post(
            f"/api/review-items/{item_id}/resolve",
            json={"action": "CONFIRM_MAPPING", "mapping": edited},
            headers=AUTH,
        )
        assert res.status_code == 200, res.text
        assert (
            res.json()["status"] == "RESOLVED"
            and res.json()["resolution"]["action"] == "CONFIRM_MAPPING"
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()

        doc = (await client.get(f"/api/documents/{DOC}", headers=AUTH)).json()
        assert doc["status"] == "DONE", doc.get("statusDetail")
        assert (
            doc["ledgerMeta"]["mappingStatus"] == "CONFIRMED"
            and doc["ledgerMeta"]["rowsImported"] == 6
        )
        assert doc["months"] == ["2026-03"]
        view = (await client.get(f"/api/documents/{DOC}/ledger-mapping", headers=AUTH)).json()
        assert view["status"] == "CONFIRMED" and view["mapping"]["description"] == "Keterangan"

    workspaces = deps.workspace_repo
    assert isinstance(workspaces, FakeWorkspaceRepository)
    workspace = await workspaces.get_workspace(ORG)
    assert workspace is not None
    stored = workspace.ledger_mappings[compute_layout_signature(HEADERS)]
    assert stored["description"] == "Keterangan" and stored["confirmedBy"] == "u-1"
    events = [e for e in workspaces.events[ORG] if e.type == "LEDGER_MAPPING_CONFIRMED"]
    assert len(events) == 1 and events[0].subject["docId"] == DOC
