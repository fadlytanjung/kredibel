"""Tests for the Finance Assistant and AI Reconciliation API (spec 011)."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice
from app.domain.models.workspace import Subscription
from app.main import AppDeps, create_app
from tests.fakes.assistant_repository import FakeAssistantRepository
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.record_repository import fake_invoices, fake_receipts
from tests.fakes.review_item_repository import FakeReviewItemRepository
from tests.fakes.usage_repository import FakeUsageRepository

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"


class _AlwaysAlice:
    def verify_token(self, token: str) -> dict[str, Any]:
        return {
            "uid": "usr_alice",
            "email": "alice@example.com",
            "orgId": "org_test",
            "role": "owner",
        }


@pytest.fixture
def test_deps():
    settings = Settings()
    plans = load_plans(PLANS_FILE)
    usage_repo = FakeUsageRepository()
    usage_repo.subscriptions["org_test"] = Subscription(plan_id="free_trial", status="ACTIVE")
    assistant_repo = FakeAssistantRepository()
    month_repo = FakeMonthRepository()
    finding_repo = FakeFindingRepository()
    bank_line_repo = FakeBankLineRepository()
    doc_repo = FakeDocumentRepository()
    review_item_repo = FakeReviewItemRepository()
    reader = FakeDocumentReader()

    invoices_repo = fake_invoices()
    receipts_repo = fake_receipts()

    deps = AppDeps(
        settings,
        plans,
        token_verifier=_AlwaysAlice(),
        usage_repo=usage_repo,
        month_repo=month_repo,
        findings=finding_repo,
        bank_lines=bank_line_repo,
        doc_repo=doc_repo,
        review_items=review_item_repo,
        invoices=invoices_repo,
        receipts=receipts_repo,
        reader=reader,
        assistant_repo=assistant_repo,
    )
    return deps, bank_line_repo, reader, invoices_repo


@pytest.mark.asyncio
async def test_assistant_threads_and_chat_lifecycle(test_deps):
    deps, bank_lines, reader, *rest = test_deps
    app = create_app(deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}

        # 1. Create a thread
        res = await client.post(
            "/api/assistant/threads",
            json={"title": "May Review", "scope": "2026-05"},
            headers=headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "May Review"
        assert data["scope"] == "2026-05"
        thread_id = data["threadId"]

        # 2. List threads
        res = await client.get("/api/assistant/threads", headers=headers)
        assert res.status_code == 200
        threads = res.json()["items"]
        assert len(threads) == 1
        assert threads[0]["threadId"] == thread_id

        # 3. List messages (empty)
        res = await client.get(f"/api/assistant/threads/{thread_id}/messages", headers=headers)
        assert res.status_code == 200
        assert res.json()["items"] == []

        # 4. Ask a question
        res = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "What is the financial situation for May 2026?"},
            headers=headers,
        )
        assert res.status_code == 200
        msg = res.json()
        assert msg["role"] == "assistant"
        assert msg["answer"] is not None
        assert len(msg["answer"]["parts"]) > 0
        assert msg["answer"]["toolsUsed"] == [
            "get_period_summary",
            "list_findings",
            "list_review_items",
        ]

        # 5. List messages (now has user and assistant messages)
        res = await client.get(f"/api/assistant/threads/{thread_id}/messages", headers=headers)
        assert res.status_code == 200
        msgs = res.json()["items"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

        # 6. Ask via SSE streaming
        stream_res = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "What were the open findings?"},
            headers={**headers, "Accept": "text/event-stream"},
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers["content-type"]
        body = stream_res.text
        assert "event: step" in body
        assert "event: tool" in body
        assert "event: token" in body
        assert "event: message" in body
        assert "event: done" in body

        # 7. Conversational greeting ("Hi") yields immediate agreed response without tool queries
        hi_res = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "Hi"},
            headers=headers,
        )
        assert hi_res.status_code == 200
        hi_msg = hi_res.json()
        assert hi_msg["role"] == "assistant"
        assert hi_msg["answer"]["grounding"]["verdict"] == "AGREED"
        assert hi_msg["answer"]["toolsUsed"] == []
        assert "Kredibel AI Finance Assistant" in hi_msg["answer"]["parts"][0]["text"]

        # 8. Conversational greeting via streaming
        stream_hi = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "Hello, what can you do?"},
            headers={**headers, "Accept": "text/event-stream"},
        )
        assert stream_hi.status_code == 200
        hi_stream_body = stream_hi.text
        assert "event: step" in hi_stream_body
        assert "event: tool" not in hi_stream_body
        assert "event: token" in hi_stream_body
        assert "event: message" in hi_stream_body
        assert "event: done" in hi_stream_body

        # 9. When reader raises an error or times out, fallback answer is returned safely
        def _failing_reader(*_a, **_kw):
            raise RuntimeError("Gemini offline")

        reader.ask_assistant = _failing_reader
        stream_fallback = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "Where did the money go in Q2?"},
            headers={**headers, "Accept": "text/event-stream"},
        )
        assert stream_fallback.status_code == 200
        fb_body = stream_fallback.text
        assert "event: message" in fb_body
        assert "event: done" in fb_body
        assert "Dashboard" in fb_body


@pytest.mark.asyncio
async def test_bank_line_ai_match_suggestion(test_deps):
    deps, bank_lines, reader, *rest = test_deps
    app = create_app(deps=deps)

    # Insert a bank line
    line = BankLine(
        tx_id="tx_test_01",
        doc_id="doc_stmt_01",
        page=1,
        row_index=0,
        date=date(2026, 5, 15),
        month="2026-05",
        amount=Decimal("-15000000"),
        balance=Decimal("50000000"),
        description="WAREHOUSE RENT MAY 2026",
        counterparty_name="TRF BCA WAREHOUSE RENT",
    )
    await bank_lines.replace_document_lines("org_test", line.doc_id, [line])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}
        res = await client.get("/api/bank-lines/tx_test_01/ai-suggestion", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "confidence" in data
        assert "reason" in data
        assert "missingDocumentAdvice" in data


@pytest.mark.asyncio
async def test_assistant_memories_lifecycle(test_deps):
    deps, *rest = test_deps
    app = create_app(deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}

        # 1. List initial memories (seeded defaults)
        res = await client.get("/api/assistant/memories", headers=headers)
        assert res.status_code == 200
        memories = res.json()["items"]
        assert len(memories) >= 1
        first_id = memories[0]["memoryId"]

        # 2. Forget single memory
        res = await client.delete(f"/api/assistant/memories/{first_id}", headers=headers)
        assert res.status_code == 204

        res = await client.get("/api/assistant/memories", headers=headers)
        assert res.status_code == 200
        remaining = res.json()["items"]
        assert all(m["memoryId"] != first_id for m in remaining)

        # 3. Forget all memories
        res = await client.delete("/api/assistant/memories", headers=headers)
        assert res.status_code == 204


@pytest.mark.asyncio
async def test_assistant_threads_pagination(test_deps):
    deps, *rest = test_deps
    app = create_app(deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}

        # Create 3 threads
        for i in range(3):
            await client.post(
                "/api/assistant/threads",
                json={"title": f"Thread {i}", "scope": "WORKSPACE"},
                headers=headers,
            )

        # Page 1 (limit 2)
        res = await client.get("/api/assistant/threads?limit=2", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert len(body["items"]) == 2
        assert body["nextCursor"] == "2"

        # Page 2 (cursor 2)
        res2 = await client.get("/api/assistant/threads?limit=2&cursor=2", headers=headers)
        assert res2.status_code == 200
        body2 = res2.json()
        assert len(body2["items"]) == 1
        assert body2["nextCursor"] is None


@pytest.mark.asyncio
async def test_assistant_diagram_request(test_deps):
    deps, *rest = test_deps
    app = create_app(deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}

        # 1. Create thread
        res = await client.post(
            "/api/assistant/threads",
            json={"title": "Diagram Test", "scope": "WORKSPACE"},
            headers=headers,
        )
        thread_id = res.json()["threadId"]

        # 2. Ask question about diagram / money flow
        res = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "Can you show me a diagram of our money flow?"},
            headers=headers,
        )
        assert res.status_code == 200
        msg = res.json()
        parts = msg["answer"]["parts"]
        assert any(p["type"] == "chart" and p["chart"] == "MONEY_FLOW" for p in parts)


@pytest.mark.asyncio
async def test_assistant_unpaid_invoices_query(test_deps):
    deps, _, _, invoices_repo = test_deps
    app = create_app(deps=deps)

    # Insert an unpaid invoice
    inv = Invoice(
        invoice_id="inv_test_unpaid_01",
        doc_id="doc_test_01",
        kind="PURCHASE",
        number="BW-0042",
        issuer_name="Bluewater Trading Co.",
        buyer_name=None,
        issue_date=date(2026, 2, 3),
        month="2026-02",
        total=Decimal("990000.00"),
        currency="IDR",
        due_date=date(2026, 2, 17),
        evidence={"payment": "UNPAID"},
    )
    await invoices_repo.replace_for_document("org_test", "doc_test_01", [inv])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer test-token"}

        # 1. Create thread
        res = await client.post(
            "/api/assistant/threads",
            json={"title": "Invoice Test", "scope": "WORKSPACE"},
            headers=headers,
        )
        thread_id = res.json()["threadId"]

        # 2. Ask "Which invoices are still unpaid?"
        res = await client.post(
            f"/api/assistant/threads/{thread_id}/messages",
            json={"question": "Which invoices are still unpaid?"},
            headers=headers,
        )
        assert res.status_code == 200
        msg = res.json()
        parts = msg["answer"]["parts"]
        # Must return INVOICE_BREAKDOWN chart
        chart_part = next((p for p in parts if p["type"] == "chart"), None)
        assert chart_part is not None
        assert chart_part["chart"] == "INVOICE_BREAKDOWN"
        assert len(chart_part["rows"]) > 0
        assert "BW-0042" in chart_part["rows"][0][0]


