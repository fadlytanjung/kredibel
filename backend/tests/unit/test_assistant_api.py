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
from app.domain.models.workspace import Subscription
from app.main import AppDeps, create_app
from tests.fakes.assistant_repository import FakeAssistantRepository
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository
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
        reader=reader,
        assistant_repo=assistant_repo,
    )
    return deps, bank_line_repo, reader


@pytest.mark.asyncio
async def test_assistant_threads_and_chat_lifecycle(test_deps):
    deps, _, _ = test_deps
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


@pytest.mark.asyncio
async def test_bank_line_ai_match_suggestion(test_deps):
    deps, bank_lines, reader = test_deps
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
    deps, _, _ = test_deps
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

