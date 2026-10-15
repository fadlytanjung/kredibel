"""The document workflow and a ledger export's column mapping (spec 005, T005-11; AC-005-11,
AC-005-12): a new layout stops at NEEDS_INPUT with a CONFIRM_LEDGER_MAPPING item; a mapping the
workspace already confirmed parses the file at once; too many bad rows reopen the item."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.agents.deps import PipelineDeps
from app.agents.workflows.document_workflow import build_document_workflow
from app.core.settings import Settings
from app.domain.ledger_parse import compute_layout_signature
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.run import Run, RunKind, RunStatus
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.ledger_repository import FakeLedgerRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.review_item_repository import FakeReviewItemRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.workspace_repository import FakeWorkspaceRepository, demo_workspace

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
ORG, DOC = "org_demo", "doc_gl_id"
trace.set_tracer_provider(TracerProvider())

# An Indonesian package's export (docs/18): local headers, day-first dates, decimal comma.
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
MAPPING = {
    "date": "Tanggal",
    "description": "Keterangan",
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


def _deps():
    workspaces = FakeWorkspaceRepository()
    workspaces.workspaces[ORG] = demo_workspace(ORG)
    deps = PipelineDeps(
        settings=Settings(),
        run_repo=FakeRunRepository(),
        doc_repo=FakeDocumentRepository(),
        month_repo=FakeMonthRepository(),
        storage=FakeDocumentStorage(),
        ledger=FakeLedgerRepository(),
        task_queue=FakeTaskQueue(),
        clock=FixedClock(NOW),
        workspaces=workspaces,
        review_items=FakeReviewItemRepository(),
    )
    return deps, workspaces


async def _run(deps: PipelineDeps, content: bytes, *, run_id: str = "doc-gl-1") -> Document:
    doc = Document(
        doc_id=DOC,
        file_name="GL_2026_Q1.csv",
        content_type="text/csv",
        size_bytes=len(content),
        page_count=0,
        sha256="c" * 64,
        gcs_path=f"gs://synthetic/{DOC}.csv",
        uploaded_by="u-1",
        uploaded_at=NOW,
        doc_type=DocType.LEDGER_EXPORT,
        status=DocStatus.UPLOADED,
    )
    existing = await deps.doc_repo.get_document(ORG, DOC)
    if existing is not None:
        doc = existing
    await deps.doc_repo.save_document(ORG, doc)
    assert deps.storage is not None
    await deps.storage.store_original(ORG, DOC, ".csv", content, "text/csv")
    await deps.run_repo.create(
        ORG, Run(run_id=run_id, kind=RunKind.DOCUMENT, target=DOC, status=RunStatus.RUNNING)
    )
    sessions = InMemorySessionService()
    runner = Runner(
        agent=cast(Any, build_document_workflow(deps)),
        app_name="kredibel",
        session_service=sessions,
    )
    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={"node_input": {"orgId": ORG, "docId": DOC, "runId": run_id, "attempt": 1}},
    )
    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass
    updated = await deps.doc_repo.get_document(ORG, DOC)
    assert updated is not None
    return updated


@pytest.mark.asyncio
async def test_ac005_11_a_new_layout_waits_for_a_person_with_the_proposal_on_a_review_item():
    deps, _ = _deps()
    doc = await _run(deps, INDONESIAN)

    assert doc.status == DocStatus.NEEDS_INPUT
    assert doc.status_detail == "Ledger mapping confirmation needed"
    meta = doc.ledger_meta or {}
    assert meta["mappingStatus"] == "PROPOSED"
    assert meta["layoutSignature"] == compute_layout_signature(HEADERS)
    assert meta["mapping"] == MAPPING
    assert meta["header"] == HEADERS and len(meta["sampleRows"]) == 5
    assert deps.ledger is not None and await deps.ledger.list_rows(ORG) == [], (
        "nothing is parsed before a person confirms"
    )

    items, _, counts = await deps.review_items.list_review_items(ORG, status="OPEN")  # type: ignore[union-attr]
    [item] = items
    assert item.kind == "CONFIRM_LEDGER_MAPPING" and item.doc_id == DOC and item.month is None
    assert item.title == "Check the columns of GL_2026_Q1.csv"
    assert (item.suggestion.mapping or {})["mapping"] == MAPPING
    assert counts == {"CONFIRM_LEDGER_MAPPING": 1}


@pytest.mark.asyncio
async def test_ac005_11_a_mapping_the_workspace_confirmed_parses_the_same_layout_at_once():
    deps, workspaces = _deps()
    signature = compute_layout_signature(HEADERS)
    ws = workspaces.workspaces[ORG]
    workspaces.workspaces[ORG] = ws.model_copy(
        update={
            "ledger_mappings": {
                signature: {**MAPPING, "confirmedBy": "u-1", "confirmedAt": NOW.isoformat()}
            }
        }
    )
    doc = await _run(deps, INDONESIAN)

    assert doc.status == DocStatus.DONE, doc.status_detail
    meta = doc.ledger_meta or {}
    assert meta["mappingStatus"] == "CONFIRMED" and meta["rowsImported"] == 6
    assert doc.months == ["2026-03"]
    assert deps.ledger is not None
    rows = await deps.ledger.list_rows(ORG)
    assert len(rows) == 6 and str(rows[0].credit) == "120000000.00"
    items, _, _ = await deps.review_items.list_review_items(ORG, status="OPEN")  # type: ignore[union-attr]
    assert items == []


@pytest.mark.asyncio
async def test_ac005_12_more_than_two_percent_bad_rows_reopen_the_mapping_item():
    deps, workspaces = _deps()
    signature = compute_layout_signature(HEADERS)
    # The person mapped the amounts the wrong way round: the description column as the debit.
    wrong = {**MAPPING, "debit": "Keterangan"}
    workspaces.workspaces[ORG] = workspaces.workspaces[ORG].model_copy(
        update={"ledger_mappings": {signature: wrong}}
    )
    doc = await _run(deps, INDONESIAN)

    assert doc.status == DocStatus.NEEDS_INPUT
    assert (doc.status_detail or "").startswith("Over 2% invalid rows")
    assert (doc.ledger_meta or {})["mappingStatus"] == "PROPOSED"
    items, _, _ = await deps.review_items.list_review_items(ORG, status="OPEN")  # type: ignore[union-attr]
    [item] = items
    assert item.kind == "CONFIRM_LEDGER_MAPPING"
    assert item.title == "6 rows of GL_2026_Q1.csv could not be read: check the columns"
    assert (item.suggestion.mapping or {})["badRows"] == [1, 2, 3, 4, 5, 6]
