"""The sync_review_items node stores the month's items and closes stale ones (T009-02, AC-009-1)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from google.adk import Context

from app.agents.deps import PipelineDeps
from app.agents.nodes.month_nodes import sync_review_items
from app.core.settings import Settings
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.invoice import Invoice
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.decision_repository import FakeDecisionRepository
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.match_repository import FakeMatchRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.record_repository import fake_invoices, fake_receipts
from tests.fakes.review_item_repository import FakeReviewItemRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository


@pytest.mark.asyncio
async def test_ac009_1_sync_review_items_node_runs_and_persists():
    org_id = "org_test"
    month = "2026-03"

    run_repo = FakeRunRepository()
    doc_repo = FakeDocumentRepository()
    month_repo = FakeMonthRepository()
    bank_lines = FakeBankLineRepository()
    invoices = fake_invoices()
    receipts = fake_receipts()
    matches = FakeMatchRepository()
    decisions = FakeDecisionRepository()
    workspaces = FakeWorkspaceRepository()
    review_items = FakeReviewItemRepository()

    deps = PipelineDeps(
        settings=Settings(),
        run_repo=run_repo,
        doc_repo=doc_repo,
        month_repo=month_repo,
        bank_lines=bank_lines,
        invoices=invoices,
        receipts=receipts,
        matches=matches,
        decisions=decisions,
        workspaces=workspaces,
        review_items=review_items,
    )

    now = datetime.now(UTC)
    # 1. Statement doc
    stmt = Document(
        doc_id="doc_stmt_1",
        file_name="stmt.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=1,
        sha256="abc",
        gcs_path="gs://test/stmt.pdf",
        uploaded_by="user_test",
        uploaded_at=now,
        doc_type=DocType.BANK_STATEMENT,
        status=DocStatus.DONE,
        months=[month],
    )
    await doc_repo.save_document(org_id, stmt)

    # 2. A bank line without support: informational (ADR-025), no item
    line = BankLine(
        tx_id="tx_1",
        doc_id="doc_stmt_1",
        page=1,
        row_index=0,
        date=datetime(2026, 3, 10).date(),
        month=month,
        description="Office supplies",
        amount=Decimal("-500000"),
        balance=None,
        counterparty_name="Stationery Store",
        support="NO_SUPPORT",
    )
    await bank_lines.replace_document_lines(org_id, "doc_stmt_1", [line])

    # 3. An invoice the month run found unpaid, and one still waiting for a statement
    unpaid = Invoice(
        invoice_id="inv_1",
        doc_id="doc_inv_1",
        kind="PURCHASE",
        number="INV-001",
        issuer_name="Coffee Bean Supplier",
        buyer_name="Sunrise Coffee",
        issue_date=datetime(2026, 3, 1).date(),
        month=month,
        total=Decimal("750000"),
        currency="IDR",
        evidence={"payment": "UNPAID"},
    )
    waiting = replace(
        unpaid,
        invoice_id="inv_2",
        doc_id="doc_inv_2",
        evidence={"payment": "WAITING_FOR_STATEMENT"},
    )
    await invoices.replace_for_document(org_id, "doc_inv_1", [unpaid])
    await invoices.replace_for_document(org_id, "doc_inv_2", [waiting])

    node = sync_review_items(deps)
    ctx = MagicMock(spec=Context)
    node_input = {"orgId": org_id, "month": month, "runId": "run_test_1", "risk": {"level": "HIGH"}}

    result = await node(ctx, node_input)
    assert result["summary"] == "1 open review item(s), 0 closed"
    (item,) = (await review_items.list_review_items(org_id, month=month))[0]
    assert (item.kind, item.subject.invoice_ids, item.priority) == (
        "UNMATCHED_DOCUMENT",
        ["inv_1"],
        65,
    )

    # Paid later: the next run closes the item, resolved by the system.
    paid = replace(unpaid, evidence={"payment": "PAID_BANK"})
    await invoices.replace_for_document(org_id, "doc_inv_1", [paid])
    result = await node(ctx, node_input)
    assert result["summary"] == "0 open review item(s), 1 closed"
    (closed,) = (await review_items.list_review_items(org_id, month=month))[0]
    assert closed.status == "RESOLVED" and closed.resolution is not None
    assert closed.resolution.resolved_by == "system"
