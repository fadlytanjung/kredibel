"""Tests for DocumentService.upload and exact duplicates (AC-003-3, AC-003-4, AC-003-5).

TDD test suite for tasks T003-03 and T003-04.
"""

import asyncio
import hashlib
import io
from datetime import UTC, datetime, timedelta

import pytest

from app.core.auth import Principal
from app.core.clock import Clock
from app.domain.errors import (
    DocumentTooLargeError,
    EncryptedDocumentError,
    NotFoundError,
    PlanLimitReachedError,
    TooManyPagesError,
    TooManyRowsError,
    TrialExpiredError,
    UnsupportedMediaTypeError,
    ValidationProblem,
)
from app.domain.models.document import DocStatus, DocType, DuplicateKind
from app.domain.models.workspace import Subscription, UsageDay, UsageMonth
from app.domain.plans import PlanCatalog
from app.services.document_service import DocumentService
from app.services.entitlement_service import EntitlementService
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository

_TEST_PLANS = """
version: 1
id: test-plans
defaultPlan: free_trial
plans:
  - id: free_trial
    label: Free trial
    status: AVAILABLE
    priceLabel: "Free for 14 days"
    trialDays: 14
    afterTrial: READ_ONLY
    limits:
      seats: 1
      documentsPerMonth: 10
      pagesPerDocument: 5
      fileSizeMb: 10
      extractedPagesPerMonth: 20
      ledgerRowsPerFile: 100
      monthRunsPerDay: 5
      aiSpendUsdPerMonth: "5.00"
      assistantQuestionsPerDay: 10
    features:
      extractionMode: adaptive
      escalation: true
      escalationPagesPerMonth: 30
      financeAssistant: true
      memberInvites: true
      monthSignOff: true
      languages: [en]
    highlights:
      - "Test highlight"
languages:
  - code: en
    label: English
    status: available
"""


@pytest.fixture
def clock() -> Clock:
    return FixedClock(datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC))


@pytest.fixture
def principal() -> Principal:
    return Principal(uid="user_123", email="user@example.com", org_id="org_test", role="owner")


@pytest.fixture
def fake_repos(clock: Clock):
    plans = PlanCatalog.model_validate(__import__("yaml").safe_load(_TEST_PLANS))
    usage_repo = FakeUsageRepository()
    # Seed active trial subscription for org_test
    usage_repo.subscriptions["org_test"] = Subscription(
        plan_id="free_trial",
        status="TRIALING",
        trial_ends_at=datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC),
    )
    usage_repo.months[("org_test", "2026-03")] = UsageMonth(month="2026-03")
    usage_repo.days[("org_test", "2026-03-15")] = UsageDay(day="2026-03-15")

    entitlements = EntitlementService(
        repo=usage_repo,
        plans=plans,
        clock=clock,
        run_quota_per_org_per_day=50,
    )
    doc_repo = FakeDocumentRepository()
    storage = FakeDocumentStorage()
    task_queue = FakeTaskQueue()

    from app.adapters.page_renderer import DefaultPageRenderer
    from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader

    renderer = DefaultPageRenderer()
    spreadsheet_reader = DefaultSpreadsheetReader()

    service = DocumentService(
        doc_repo=doc_repo,
        storage=storage,
        task_queue=task_queue,
        entitlements=entitlements,
        renderer=renderer,
        clock=clock,
        spreadsheet_reader=spreadsheet_reader,
    )
    return service, doc_repo, storage, task_queue, usage_repo


def _create_minimal_pdf_bytes(page_count: int = 1) -> bytes:
    from PIL import Image

    imgs = [Image.new("RGB", (100, 100), color=(50, 50, 50)) for _ in range(page_count)]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_valid_pdf_success(fake_repos, principal: Principal):
    service, doc_repo, storage, task_queue, usage_repo = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=2)

    doc = await service.upload(
        principal=principal,
        file_bytes=pdf_bytes,
        filename="bank_statement.pdf",
    )

    assert doc.status == DocStatus.UPLOADED
    assert doc.doc_type == DocType.UNKNOWN
    assert doc.page_count == 2
    assert doc.file_name == "bank_statement.pdf"
    assert doc.counts_against_limits is True
    assert doc.duplicate is None

    # Storage has original and pages
    assert len(storage.originals) == 1
    assert len(storage.pages) == 4  # 2 pages * (full + thumb)

    # Task enqueued
    assert len(task_queue.enqueued_tasks) == 1
    assert task_queue.enqueued_tasks[0][1] == doc.doc_id

    # Repository persisted document and event
    assert (principal.org_id, doc.doc_id) in doc_repo.documents
    assert len(doc_repo.events) == 1
    assert doc_repo.events[0][1].type == "DOCUMENT_UPLOADED"

    # Usage metered: 1 document, 2 pages
    month_usage = usage_repo.months[("org_test", "2026-03")]
    assert month_usage.documents_uploaded == 1
    assert month_usage.pages_reserved == 2


@pytest.mark.asyncio
async def test_upload_with_doc_type_hint(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)

    doc = await service.upload(
        principal=principal,
        file_bytes=pdf_bytes,
        filename="invoice.pdf",
        doc_type_hint=DocType.SALES_INVOICE,
    )

    assert doc.doc_type == DocType.SALES_INVOICE


@pytest.mark.asyncio
async def test_upload_unsupported_media_type_raises_415(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos
    # Random binary or executable
    data = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"

    with pytest.raises(UnsupportedMediaTypeError):
        await service.upload(principal=principal, file_bytes=data, filename="bad.bin")


@pytest.mark.asyncio
async def test_upload_empty_file_raises_422(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos

    with pytest.raises(ValidationProblem) as exc_info:
        await service.upload(principal=principal, file_bytes=b"", filename="empty.pdf")
    assert exc_info.value.code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_upload_file_too_large_raises_413(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos
    # Limit is 10 MB in test plan. Create 11 MB dummy PDF header
    large_pdf = b"%PDF-1.4\n" + (b"0" * (11 * 1024 * 1024))

    with pytest.raises(DocumentTooLargeError):
        await service.upload(principal=principal, file_bytes=large_pdf, filename="large.pdf")


@pytest.mark.asyncio
async def test_upload_too_many_pages_raises_422(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos
    # Limit is 5 pages per document in test plan. Create 6 pages.
    many_pages_pdf = _create_minimal_pdf_bytes(page_count=6)

    with pytest.raises(TooManyPagesError):
        await service.upload(principal=principal, file_bytes=many_pages_pdf, filename="many.pdf")


@pytest.mark.asyncio
async def test_upload_too_many_rows_raises_422(fake_repos, principal: Principal):
    service, _, _, _, _ = fake_repos
    # Limit is 100 ledger rows in test plan. Create 105 rows.
    csv_data = "Date,Account,Description,Amount\n" + "\n".join(
        f"2026-03-01,1000,Row {i},10.00" for i in range(105)
    )

    with pytest.raises(TooManyRowsError):
        await service.upload(
            principal=principal, file_bytes=csv_data.encode("utf-8"), filename="large_ledger.csv"
        )


@pytest.mark.asyncio
async def test_upload_encrypted_pdf_raises_422(fake_repos, principal: Principal):
    import pikepdf

    service, _, _, _, _ = fake_repos
    doc = pikepdf.Pdf.new()
    doc.add_blank_page()
    buf = io.BytesIO()
    doc.save(buf, encryption=pikepdf.Encryption(owner="secret", user="secret"))
    encrypted_bytes = buf.getvalue()

    with pytest.raises(EncryptedDocumentError):
        await service.upload(
            principal=principal, file_bytes=encrypted_bytes, filename="encrypted.pdf"
        )


@pytest.mark.asyncio
async def test_upload_trial_expired_raises_403(fake_repos, principal: Principal):
    service, _, _, _, usage_repo = fake_repos
    # Expire trial
    usage_repo.subscriptions["org_test"] = Subscription(
        plan_id="free_trial",
        status="TRIAL_EXPIRED",
        trial_ends_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
    )
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)

    with pytest.raises(TrialExpiredError):
        await service.upload(principal=principal, file_bytes=pdf_bytes, filename="statement.pdf")


@pytest.mark.asyncio
async def test_upload_exact_duplicate(fake_repos, principal: Principal):
    service, doc_repo, storage, task_queue, usage_repo = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)

    # 1. First upload -> original document
    original = await service.upload(
        principal=principal,
        file_bytes=pdf_bytes,
        filename="Original_BCA.pdf",
    )
    assert original.status == DocStatus.UPLOADED
    assert original.counts_against_limits is True
    assert len(storage.originals) == 1
    assert len(task_queue.enqueued_tasks) == 1

    # Usage after 1st upload
    month_usage = usage_repo.months[("org_test", "2026-03")]
    assert month_usage.documents_uploaded == 1
    assert month_usage.pages_reserved == 1

    # 2. Second upload with identical bytes
    duplicate = await service.upload(
        principal=principal,
        file_bytes=pdf_bytes,
        filename="Duplicate_BCA.pdf",
    )

    # Assertions for exact duplicate (AC-003-5)
    assert duplicate.status == DocStatus.DUPLICATE
    assert duplicate.counts_against_limits is False
    assert duplicate.duplicate is not None
    assert duplicate.duplicate.kind == DuplicateKind.EXACT
    assert duplicate.duplicate.code == "D01_EXACT_FILE_DUPLICATE"
    assert duplicate.duplicate.of_doc_id == original.doc_id

    # No new file stored in GCS
    assert len(storage.originals) == 1
    # No new task enqueued
    assert len(task_queue.enqueued_tasks) == 1

    # Usage unchanged
    month_usage_after = usage_repo.months[("org_test", "2026-03")]
    assert month_usage_after.documents_uploaded == 1
    assert month_usage_after.pages_reserved == 1

    # DUPLICATE_RECORDED event logged
    assert len(doc_repo.events) == 2
    assert doc_repo.events[1][1].type == "DUPLICATE_RECORDED"
    assert doc_repo.events[1][1].subject["docId"] == duplicate.doc_id
    assert doc_repo.events[1][1].subject["ofDocId"] == original.doc_id


@pytest.mark.asyncio
async def test_get_document_success(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, _, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    uploaded = await service.upload(principal, pdf_bytes, "test.pdf")

    fetched = await service.get_document(principal, uploaded.doc_id)
    assert fetched.doc_id == uploaded.doc_id
    assert fetched.file_name == "test.pdf"


@pytest.mark.asyncio
async def test_get_document_foreign_or_missing_raises_404(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, _, _, _ = fake_repos
    with pytest.raises(NotFoundError):
        await service.get_document(principal, "nonexistent_doc")

    foreign_principal = Principal(uid="user2", org_id="org_other", email="other@example.com")
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    uploaded = await service.upload(principal, pdf_bytes, "test.pdf")

    # Foreign workspace request raises NotFoundError (AC-003-11)
    with pytest.raises(NotFoundError):
        await service.get_document(foreign_principal, uploaded.doc_id)


@pytest.mark.asyncio
async def test_list_documents_filtering(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, _, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    doc1 = await service.upload(principal, pdf_bytes, "doc1.pdf")
    doc2 = await service.upload(principal, pdf_bytes, "doc2.pdf")  # exact duplicate

    docs, _ = await service.list_documents(principal)
    assert len(docs) == 2

    # Filter duplicate=True
    dup_docs, _ = await service.list_documents(principal, duplicate=True)
    assert len(dup_docs) == 1
    assert dup_docs[0].doc_id == doc2.doc_id

    # Filter duplicate=False
    non_dup, _ = await service.list_documents(principal, duplicate=False)
    assert len(non_dup) == 1
    assert non_dup[0].doc_id == doc1.doc_id


@pytest.mark.asyncio
async def test_get_file_and_exact_duplicate(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, _, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    doc1 = await service.upload(principal, pdf_bytes, "doc1.pdf")
    doc2 = await service.upload(principal, pdf_bytes, "doc2.pdf")

    # Both original and duplicate serve the file bytes
    data1, content_type1 = await service.get_file(principal, doc1.doc_id)
    assert data1 == pdf_bytes
    assert content_type1 == "application/pdf"

    data2, content_type2 = await service.get_file(principal, doc2.doc_id)
    assert data2 == pdf_bytes
    assert content_type2 == "application/pdf"

    # Foreign principal gets 404 (AC-003-11)
    foreign = Principal(uid="user2", org_id="org_other", email="other@example.com")
    with pytest.raises(NotFoundError):
        await service.get_file(foreign, doc1.doc_id)


@pytest.mark.asyncio
async def test_get_page_image_and_exact_duplicate(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, _, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    doc1 = await service.upload(principal, pdf_bytes, "doc1.pdf")
    doc2 = await service.upload(principal, pdf_bytes, "doc2.pdf")

    img1 = await service.get_page_image(principal, doc1.doc_id, page_no=1)
    assert len(img1) > 0
    thumb1 = await service.get_page_image(principal, doc1.doc_id, page_no=1, thumb=True)
    assert len(thumb1) > 0

    # Duplicate gets page image from original
    img2 = await service.get_page_image(principal, doc2.doc_id, page_no=1)
    assert img2 == img1

    # Out of bounds page raises NotFoundError
    with pytest.raises(NotFoundError):
        await service.get_page_image(principal, doc1.doc_id, page_no=99)

    # Foreign principal gets NotFoundError (AC-003-11)
    foreign = Principal(uid="user2", org_id="org_other", email="other@example.com")
    with pytest.raises(NotFoundError):
        await service.get_page_image(foreign, doc1.doc_id, page_no=1)


@pytest.mark.asyncio
async def test_delete_document_original_cascades_and_marks_months_dirty(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, doc_repo, storage, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    doc1 = await service.upload(principal, pdf_bytes, "doc1.pdf")
    doc2 = await service.upload(principal, pdf_bytes, "doc2.pdf")  # duplicate of doc1

    # Set months on doc1
    object.__setattr__(doc1, "months", ["2026-03"])

    # Delete original doc1 (AC-003-10)
    await service.delete_document(principal, doc1.doc_id)

    # doc1 is removed from repo and storage
    with pytest.raises(NotFoundError):
        await service.get_document(principal, doc1.doc_id)
    assert len(storage.originals) == 0

    # Exact duplicate doc2 is also removed by cascade (original-of-duplicate rule, AC-003-10)
    with pytest.raises(NotFoundError):
        await service.get_document(principal, doc2.doc_id)

    # Month is marked dirty
    assert doc_repo.dirty_months.get(("org_test", "2026-03")) == 1

    # DOCUMENT_REMOVED event logged
    events = [e for _, e in doc_repo.events if e.type == "DOCUMENT_REMOVED"]
    assert len(events) == 1
    assert events[0].subject["docId"] == doc1.doc_id


@pytest.mark.asyncio
async def test_delete_document_duplicate_preserves_original(
    principal: Principal,
    fake_repos: tuple[
        DocumentService,
        FakeDocumentRepository,
        FakeDocumentStorage,
        FakeTaskQueue,
        FakeUsageRepository,
    ],
) -> None:
    service, _, storage, _, _ = fake_repos
    pdf_bytes = _create_minimal_pdf_bytes(page_count=1)
    doc1 = await service.upload(principal, pdf_bytes, "doc1.pdf")
    doc2 = await service.upload(principal, pdf_bytes, "doc2.pdf")  # duplicate of doc1

    # Delete duplicate doc2
    await service.delete_document(principal, doc2.doc_id)

    # doc2 is removed
    with pytest.raises(NotFoundError):
        await service.get_document(principal, doc2.doc_id)

    # Original doc1 still exists and storage is preserved
    original = await service.get_document(principal, doc1.doc_id)
    assert original.doc_id == doc1.doc_id
    assert len(storage.originals) == 1


# ---------------------------------------------------------------------------- simultaneous uploads
# Two uploads of a 13-page statement 3 ms apart both became originals and both counted against the
# limits: the SHA-256 lookup and the document write were not one transaction (spec 003 plan).


async def _no_wait(_seconds: float) -> None:
    await asyncio.sleep(0)


async def test_two_simultaneous_uploads_make_one_original_and_one_duplicate(fake_repos, principal):
    service, doc_repo, _storage, task_queue, usage_repo = fake_repos
    service._sleep = _no_wait
    pdf = _create_minimal_pdf_bytes(page_count=2)

    first, second = await asyncio.gather(
        service.upload(principal=principal, file_bytes=pdf, filename="RHB.pdf"),
        service.upload(principal=principal, file_bytes=pdf, filename="RHB.pdf"),
    )

    statuses = sorted([first.status, second.status])
    assert statuses == sorted([DocStatus.UPLOADED, DocStatus.DUPLICATE])
    original, copy = (first, second) if first.status == DocStatus.UPLOADED else (second, first)
    assert copy.duplicate is not None and copy.duplicate.of_doc_id == original.doc_id
    assert copy.counts_against_limits is False
    assert usage_repo.months[("org_test", "2026-03")].documents_uploaded == 1
    assert len(task_queue.enqueued_tasks) == 1


async def test_a_failed_upload_releases_the_content(fake_repos, principal):
    service, doc_repo, _storage, _queue, usage_repo = fake_repos
    pdf = _create_minimal_pdf_bytes()
    usage_repo.months[("org_test", "2026-03")] = UsageMonth(month="2026-03", documents_uploaded=10)

    with pytest.raises(PlanLimitReachedError):
        await service.upload(principal=principal, file_bytes=pdf, filename="a.pdf")
    assert doc_repo.claims == {}

    usage_repo.months[("org_test", "2026-03")] = UsageMonth(month="2026-03")
    again = await service.upload(principal=principal, file_bytes=pdf, filename="a.pdf")
    assert again.status == DocStatus.UPLOADED


async def test_a_document_from_before_the_registry_is_still_the_original(fake_repos, principal):
    service, doc_repo, _storage, _queue, _usage = fake_repos
    pdf = _create_minimal_pdf_bytes()
    legacy = await service.upload(principal=principal, file_bytes=pdf, filename="old.pdf")
    doc_repo.claims.clear()  # as if uploaded before fileHashes existed

    again = await service.upload(principal=principal, file_bytes=pdf, filename="old (1).pdf")

    assert again.status == DocStatus.DUPLICATE
    assert again.duplicate is not None and again.duplicate.of_doc_id == legacy.doc_id


async def test_deleting_the_original_frees_the_content(fake_repos, principal):
    service, doc_repo, _storage, _queue, _usage = fake_repos
    pdf = _create_minimal_pdf_bytes()
    first = await service.upload(principal=principal, file_bytes=pdf, filename="a.pdf")
    await doc_repo.delete_document("org_test", first.doc_id)

    again = await service.upload(principal=principal, file_bytes=pdf, filename="a.pdf")
    assert again.status == DocStatus.UPLOADED and again.doc_id != first.doc_id


async def test_a_stale_claim_whose_document_never_appeared_is_taken_over(
    fake_repos, principal, clock
):
    service, doc_repo, _storage, _queue, _usage = fake_repos
    pdf = _create_minimal_pdf_bytes()
    sha = hashlib.sha256(pdf).hexdigest()
    doc_repo.claims[("org_test", sha)] = ("doc_crashed", clock.now() - timedelta(minutes=11))

    doc = await service.upload(principal=principal, file_bytes=pdf, filename="a.pdf")
    assert doc.status == DocStatus.UPLOADED
    assert doc_repo.claims[("org_test", sha)][0] == doc.doc_id
