"""`GET /api/dashboard` answers in ≤ 500 ms p95 on S1's books (spec 010, T010-03; AC-010-10).

The books live in the Firestore emulator (every store the dashboard reads), seeded as the document
workflow leaves them and reconciled by the month runs; the figures and flows are precomputed, so
a request aggregates months. Skips without the emulator (`make docker-up`). Synthetic data only.
"""

import time
import uuid

from google.cloud.firestore import AsyncClient

from app.adapters.firestore.bank_line_repo import FirestoreBankLineRepository
from app.adapters.firestore.decision_repo import FirestoreDecisionRepository
from app.adapters.firestore.document_repo import FirestoreDocumentRepository
from app.adapters.firestore.finding_repo import FirestoreFindingRepository
from app.adapters.firestore.ledger_repo import FirestoreLedgerRepository
from app.adapters.firestore.match_repo import FirestoreMatchRepository
from app.adapters.firestore.month_repo import FirestoreMonthRepository
from app.adapters.firestore.record_repo import firestore_invoices, firestore_receipts
from app.adapters.firestore.review_item_repo import FirestoreReviewItemRepo
from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client

SAMPLES = 20
BUDGET_SECONDS = 0.5


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, round(0.95 * len(ordered)) - 1)]


async def test_ac010_10_the_dashboard_answers_within_500ms_p95_on_s1(firestore_emulator):
    truth = books.load_truth("S1")
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    deps = books.books_deps()
    deps._doc_repo = FirestoreDocumentRepository(db)
    deps._month_repo = FirestoreMonthRepository(db)
    deps._bank_lines = FirestoreBankLineRepository(db)
    deps._invoices = firestore_invoices(db)
    deps._receipts = firestore_receipts(db)
    deps._findings = FirestoreFindingRepository(db)
    deps._decisions = FirestoreDecisionRepository(db)
    deps._matches = FirestoreMatchRepository(db)
    deps._review_items = FirestoreReviewItemRepo(db)
    deps._ledger = FirestoreLedgerRepository(db)
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)

        timings: dict[str, float] = {}
        body: dict = {}
        for period in ("recent", "2026-01..2026-06", "2026-Q1"):
            samples: list[float] = []
            for _ in range(SAMPLES):
                started = time.perf_counter()
                res = await client.get("/api/dashboard", params={"period": period}, headers=AUTH)
                samples.append(time.perf_counter() - started)
                assert res.status_code == 200, res.text
                body = res.json()
            timings[period] = _p95(samples)

    print("dashboard p95:", {period: f"{p95 * 1000:.0f} ms" for period, p95 in timings.items()})
    assert body["period"] == "2026-Q1"
    assert all(p95 <= BUDGET_SECONDS for p95 in timings.values()), {
        period: f"{p95 * 1000:.0f} ms" for period, p95 in timings.items()
    }
