"""AC-018-1/2/4: server-scoped reporting and audited account decisions."""

from app.domain.profit_loss import Classification
from tests.fakes.ledger_repository import FakeLedgerRepository
from tests.integration.test_invoice_workflow import AUTH, _client, _deps
from tests.unit.test_profit_loss import mappings, row


async def test_ac018_scoped_report_classification_and_validation():
    deps, _ = _deps()
    repo = FakeLedgerRepository()
    deps._ledger = repo
    repo.rows["org_1"] = [row("sales", credit="100"), row("bank", debit="100")]
    repo.rows["org_foreign"] = [row("secret", credit="999")]
    repo.mappings["org_1"] = mappings()
    async with _client(deps) as client:
        # No source document is trusted just because a row names it.
        report = await client.get("/api/profit-loss?period=2026-03", headers=AUTH)
        assert report.status_code == 200
        assert report.json()["status"] == "UNAVAILABLE"
        assert report.json()["exclusions"]["SOURCE_UNAVAILABLE"] == 2
        accounts = await client.get("/api/profit-loss/accounts", headers=AUTH)
        assert {a["accountCode"] for a in accounts.json()["accounts"]} == {"sales", "bank"}
        decision = Classification(account_code="sales", pnl_line="REVENUE", subledger="GENERAL")
        response = await client.put(
            "/api/profit-loss/accounts", headers=AUTH, json=decision.model_dump(by_alias=True)
        )
        assert response.status_code == 200
        assert repo.events[-1].actor_uid == "u-1"
        assert repo.mappings["org_1"]["sales"].subledger == "GENERAL"
        bad = await client.put(
            "/api/profit-loss/accounts",
            headers=AUTH,
            json={"accountCode": "sales", "pnlLine": "GUESS", "subledger": "GENERAL"},
        )
        assert bad.status_code == 422
        foreign = await client.put(
            "/api/profit-loss/accounts",
            headers=AUTH,
            json={"accountCode": "secret", "pnlLine": "REVENUE", "subledger": "GENERAL"},
        )
        assert foreign.status_code == 422
        invalid = await client.get("/api/profit-loss?period=2026-03..2026-01", headers=AUTH)
        assert invalid.status_code == 422
        unauth = await client.get("/api/profit-loss")
        assert unauth.status_code == 401


async def test_ac018_2_roles_and_6_assistant_use_the_same_report():
    from datetime import UTC, datetime

    from app.domain.models.document import DocStatus, DocType, Document
    from tests.fakes.assistant_repository import FakeAssistantRepository
    from tests.unit.test_auth import FakeTokenVerifier

    deps, _ = _deps()
    repo = FakeLedgerRepository()
    deps._ledger = repo
    deps._assistant_repo = FakeAssistantRepository()
    deps._token_verifier = FakeTokenVerifier(
        {
            "owner": {"uid": "u-1", "orgId": "org_1", "role": "owner"},
            "viewer": {"uid": "u-2", "orgId": "org_1", "role": "viewer"},
            "foreign": {"uid": "u-3", "orgId": "org_other", "role": "owner"},
        }
    )
    repo.rows["org_1"] = [row("sales", credit="100.10"), row("bank", debit="100.10")]
    repo.mappings["org_1"] = mappings()
    doc = Document(
        doc_id="doc_synthetic",
        file_name="synthetic.csv",
        content_type="text/csv",
        size_bytes=1,
        page_count=0,
        sha256="synthetic",
        gcs_path="synthetic",
        uploaded_by="u-1",
        uploaded_at=datetime(2026, 3, 3, tzinfo=UTC),
        doc_type=DocType.LEDGER_EXPORT,
        status=DocStatus.DONE,
    )
    from tests.fakes.document_repository import FakeDocumentRepository

    assert isinstance(deps.doc_repo, FakeDocumentRepository)
    deps.doc_repo.documents[("org_1", doc.doc_id)] = doc
    async with _client(deps) as client:
        report = (await client.get("/api/profit-loss?period=2026-03", headers=AUTH)).json()
        assert report["status"] == "IMPORTED"
        assert report["lines"][-1]["amount"] == "100.10"
        denied = await client.put(
            "/api/profit-loss/accounts",
            headers={"Authorization": "Bearer viewer"},
            json={"accountCode": "sales", "pnlLine": "REVENUE", "subledger": "GENERAL"},
        )
        assert denied.status_code == 403 and repo.events == []
        accounts = await client.get(
            "/api/profit-loss/accounts", headers={"Authorization": "Bearer foreign"}
        )
        assert accounts.json()["accounts"] == []
        thread = (
            await client.post("/api/assistant/threads", headers=AUTH, json={"scope": "2026-03"})
        ).json()["threadId"]
        path = f"/api/assistant/threads/{thread}/messages"
        message = (
            await client.post(path, headers=AUTH, json={"question": "Show profit and loss"})
        ).json()
        assert message["answer"]["toolsUsed"] == ["get_profit_loss"]
        assert message["answer"]["citations"][-1]["ref"] == report["lines"][-1]["factId"]
        streamed = await client.post(
            path, headers={**AUTH, "Accept": "text/event-stream"}, json={"question": "Show my P&L"}
        )
        assert "PROFIT_LOSS" in streamed.text and "event: message" in streamed.text
        assert "event: token" not in streamed.text
