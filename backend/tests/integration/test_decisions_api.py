"""A person's decisions (spec 007, T007-06a, AC-007-16, AC-007-19; ADR-025) through the API.

Uses the read synthetic invoice (IDR workspace "Sunrise Coffee Roasters"). No decision creates bank
cash or a match; each is audited and makes the months concerned re-reconcile."""

from app.adapters.cloud_tasks import InlineTaskQueue
from tests.integration.test_invoice_workflow import AUTH, _client, _deps, _upload


async def _read_invoice(client, deps) -> tuple[str, str]:
    doc_id = await _upload(client, deps)
    [inv] = (await client.get("/api/invoices", params={"docId": doc_id}, headers=AUTH)).json()[
        "items"
    ]
    return doc_id, inv["invoiceId"]


async def test_a_payment_confirmation_is_recorded_audited_and_reruns_its_months():
    deps, _ = _deps()
    async with _client(deps) as client:
        doc_id, invoice_id = await _read_invoice(client, deps)
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        before = len(queue.enqueued_month_tasks)
        body = {
            "kind": "PAYMENT_CONFIRMATION",
            "invoiceId": invoice_id,
            "paidOn": "2026-03-20",
            "amount": {"amount": "5000000.00", "currency": "IDR"},
            "method": "TRANSFER",
            "reason": "Paid from the owner's personal account",
        }
        res = await client.post("/api/decisions", json=body, headers=AUTH)
        listed = (
            await client.get("/api/decisions", params={"recordId": invoice_id}, headers=AUTH)
        ).json()

    assert res.status_code == 201, res.text
    d = res.json()
    assert (d["kind"], d["status"], d["amount"], d["docId"]) == (
        "PAYMENT_CONFIRMATION",
        "ACTIVE",
        {"amount": "5000000.00", "currency": "IDR"},
        doc_id,
    )
    assert d["decisionId"].startswith("dec_") and d["months"] == ["2026-03"]
    assert [x["decisionId"] for x in listed["items"]] == [d["decisionId"]]
    assert [t["month"] for t in queue.enqueued_month_tasks[before:]] == ["2026-03"]
    assert [e.type for e in deps.decisions.events] == ["DECISION_RECORDED"]  # type: ignore[attr-defined]


async def test_a_payment_confirmation_is_in_the_workspace_currency_and_within_the_total():
    deps, _ = _deps()
    async with _client(deps) as client:
        _, invoice_id = await _read_invoice(client, deps)
        base = {
            "kind": "PAYMENT_CONFIRMATION",
            "invoiceId": invoice_id,
            "paidOn": "2026-03-20",
            "method": "CASH",
            "reason": "Paid at the counter",
        }
        foreign = await client.post(
            "/api/decisions",
            headers=AUTH,
            json={**base, "amount": {"amount": "100.00", "currency": "MYR"}},
        )
        too_much = await client.post(
            "/api/decisions",
            headers=AUTH,
            json={**base, "amount": {"amount": "99999999.00", "currency": "IDR"}},
        )
        no_reason = await client.post(
            "/api/decisions",
            headers=AUTH,
            json={**base, "reason": None, "amount": {"amount": "1.00", "currency": "IDR"}},
        )
    assert foreign.status_code == 422 and "does not convert" in foreign.text
    assert too_much.status_code == 422 and "more than the document" in too_much.text
    assert no_reason.status_code == 422


async def test_approval_is_one_per_document_and_withdrawing_keeps_the_history():
    deps, _ = _deps()
    async with _client(deps) as client:
        doc_id, _ = await _read_invoice(client, deps)
        first = (
            await client.post(
                "/api/decisions", json={"kind": "DOCUMENT_APPROVAL", "docId": doc_id}, headers=AUTH
            )
        ).json()
        again = (
            await client.post(
                "/api/decisions", json={"kind": "DOCUMENT_APPROVAL", "docId": doc_id}, headers=AUTH
            )
        ).json()
        withdrawn = await client.delete(f"/api/decisions/{first['decisionId']}", headers=AUTH)
        listed = (await client.get("/api/decisions", params={"docId": doc_id}, headers=AUTH)).json()
        missing = await client.post(
            "/api/decisions", json={"kind": "DOCUMENT_APPROVAL", "docId": "doc_nope"}, headers=AUTH
        )
    assert first["decisionId"] == again["decisionId"]
    assert withdrawn.status_code == 204
    assert [(x["status"], bool(x["withdrawnAt"])) for x in listed["items"]] == [("WITHDRAWN", True)]
    assert [e.type for e in deps.decisions.events] == ["DECISION_RECORDED", "DECISION_WITHDRAWN"]  # type: ignore[attr-defined]
    assert missing.status_code == 404


async def test_currency_agreement_only_for_a_document_in_another_currency():
    deps, _ = _deps()
    async with _client(deps) as client:
        doc_id, _ = await _read_invoice(client, deps)
        same = await client.post(
            "/api/decisions", json={"kind": "CURRENCY_AGREEMENT", "docId": doc_id}, headers=AUTH
        )
        workspace = deps.workspace_repo.workspaces["org_1"]  # type: ignore[attr-defined]
        deps.workspace_repo.workspaces["org_1"] = workspace.model_copy(update={"currency": "MYR"})  # type: ignore[attr-defined]
        agreed = await client.post(
            "/api/decisions", json={"kind": "CURRENCY_AGREEMENT", "docId": doc_id}, headers=AUTH
        )
    assert same.status_code == 422
    assert agreed.status_code == 201
    assert (agreed.json()["printedCurrency"], agreed.json()["kind"]) == (
        "IDR",
        "CURRENCY_AGREEMENT",
    )


async def test_support_not_required_needs_a_reason_and_a_real_line():
    deps, _ = _deps()
    async with _client(deps) as client:
        no_reason = await client.post(
            "/api/decisions", json={"kind": "SUPPORT_NOT_REQUIRED", "txId": "tx_1"}, headers=AUTH
        )
        unknown = await client.post(
            "/api/decisions",
            headers=AUTH,
            json={"kind": "SUPPORT_NOT_REQUIRED", "txId": "tx_nope", "reason": "Bank fee"},
        )
    assert no_reason.status_code == 422
    assert unknown.status_code == 404
