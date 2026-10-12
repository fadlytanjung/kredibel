"""Bank lines on Firestore (docs/09 §3.6): upsert by ID, drop lines a re-read no longer has."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.bank_line_repo import FirestoreBankLineRepository
from app.domain.models.bank_line import BankLine


def _line(tx: str, doc: str, row: int, day: int, amount: str, month: str = "2026-09") -> BankLine:
    box = {"x0": 0.6, "y0": 0.3, "x1": 0.7, "y1": 0.31}
    return BankLine(
        tx_id=tx,
        doc_id=doc,
        page=1,
        row_index=row,
        date=date(2026, int(month[-2:]), day),
        month=month,
        description="DUITNOW TRF DR\nKEDAI RUNCIT",
        amount=Decimal(amount),
        balance=Decimal("1204.33"),
        counterparty_name="KEDAI RUNCIT",
        chunk_ids=("p1-c4",),
        consensus={
            "amount": {
                "status": "AGREED",
                "page": 1,
                "bbox": box,
                "raw": {"GEMINI": amount, "TEXT_LAYER": amount},
            }
        },
    )


@pytest.fixture
def repo(firestore_emulator: str) -> FirestoreBankLineRepository:
    return FirestoreBankLineRepository(AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}"))


async def test_lines_round_trip_with_their_grounding(repo):
    await repo.replace_document_lines(
        "org_1",
        "doc_a",
        [_line("tx_2", "doc_a", 2, 3, "-12.40"), _line("tx_1", "doc_a", 1, 2, "250.00")],
    )
    got = await repo.list_lines("org_1", doc_id="doc_a")
    assert [ln.tx_id for ln in got] == ["tx_1", "tx_2"]
    assert got[1].amount == Decimal("-12.40")
    assert got[1].balance == Decimal("1204.33")
    assert got[1].consensus["amount"]["bbox"]["x0"] == 0.6
    assert got[1].chunk_ids == ("p1-c4",)


async def test_a_re_read_drops_the_lines_it_no_longer_has_and_keeps_other_documents(repo):
    await repo.replace_document_lines(
        "org_1",
        "doc_a",
        [_line("tx_1", "doc_a", 1, 2, "1.00"), _line("tx_2", "doc_a", 2, 3, "2.00")],
    )
    await repo.replace_document_lines("org_1", "doc_b", [_line("tx_9", "doc_b", 1, 4, "9.00")])
    await repo.replace_document_lines("org_1", "doc_a", [_line("tx_2", "doc_a", 1, 3, "2.50")])

    assert [(ln.tx_id, ln.amount) for ln in await repo.list_lines("org_1", doc_id="doc_a")] == [
        ("tx_2", Decimal("2.50"))
    ]
    assert [ln.tx_id for ln in await repo.list_lines("org_1", doc_id="doc_b")] == ["tx_9"]

    await repo.replace_document_lines("org_1", "doc_a", [])
    assert await repo.list_lines("org_1", doc_id="doc_a") == []


async def test_lines_filter_by_month(repo):
    await repo.replace_document_lines(
        "org_1",
        "doc_a",
        [_line("tx_1", "doc_a", 1, 20, "1.00", "2026-08"), _line("tx_2", "doc_a", 2, 3, "2.00")],
    )
    assert [ln.tx_id for ln in await repo.list_lines("org_1", month="2026-08")] == ["tx_1"]
    assert [ln.tx_id for ln in await repo.list_lines("org_1", doc_id="doc_a", month="2026-09")] == [
        "tx_2"
    ]
