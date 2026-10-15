"""Documents may precede statements; a person's decision survives later bank evidence."""

from copy import deepcopy

from app.adapters.cloud_tasks import InlineTaskQueue
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.integration.test_invoice_workflow import AUTH, PDF, _client, _deps, _recorded
from tests.integration.test_month_workflow_reconcile import STATEMENT, _classify, _upload
from tests.integration.test_reading_workflow import _recorded_page


async def drain(deps):
    assert isinstance(deps.task_queue, InlineTaskQueue)
    await deps.task_queue.drain()


async def invoice(client):
    return (await client.get("/api/invoices", headers=AUTH)).json()["items"][0]


async def month(client):
    return (await client.get("/api/months/2026-03", headers=AUTH)).json()


async def decide(client, deps, **body):
    result = await client.post("/api/decisions", headers=AUTH, json=body)
    assert result.status_code == 201, result.text
    await drain(deps)
    return result.json()


async def test_invoice_first_approval_payment_confirmation_then_bank_evidence():
    deps, _ = _deps()
    deps._reader = FakeDocumentReader(_classify, pages=_recorded_page, invoice_pages=_recorded)
    async with _client(deps) as client:
        doc = await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")
        inv = await invoice(client)
        assert inv["evidence"]["payment"] == "WAITING_FOR_STATEMENT"
        assert inv["payment"]["state"] == "WAITING_FOR_STATEMENT"
        assert (await month(client))["state"] == "COLLECTING"
        await decide(client, deps, kind="DOCUMENT_APPROVAL", docId=doc)
        inv = await invoice(client)
        assert inv["evidence"]["approved"]
        assert inv["evidence"]["payment"] == "WAITING_FOR_STATEMENT"

        await decide(
            client,
            deps,
            kind="PAYMENT_CONFIRMATION",
            invoiceId=inv["invoiceId"],
            amount=inv["total"],
            paidOn="2026-03-21",
            method="TRANSFER",
            reason="Confirmed against the synthetic payment record",
        )
        assert (await invoice(client))["evidence"]["payment"] == "CONFIRMED_BY_YOU"
        assert (await month(client))["figures"]["moneyIn"]["value"] == "0.00"
        await _upload(client, deps, STATEMENT, "march.pdf")
        inv = await invoice(client)
        assert inv["evidence"]["payment"] == "PAID_BANK"
        assert inv["payment"]["state"] == "PAID"
        assert inv["evidence"]["approved"]
        assert inv["evidence"]["outstanding"]["amount"] == "0.00"
        assert inv["evidence"]["confirmedPaid"] == inv["evidence"]["bankPaid"] == inv["total"]


async def test_currency_pending_is_excluded_then_numbers_are_used_unchanged_in_workspace_currency():
    deps, _ = _deps()
    workspace = await deps.workspace_repo.get_workspace("org_1")
    assert workspace is not None and isinstance(deps.workspace_repo, FakeWorkspaceRepository)
    deps.workspace_repo.workspaces["org_1"] = workspace.model_copy(update={"currency": "MYR"})
    async with _client(deps) as client:
        doc = await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")
        inv = await invoice(client)
        assert inv["evidence"]["payment"] == "CURRENCY_TO_CONFIRM"
        assert (await month(client))["figures"]["invoicedSales"]["value"] == "0.00"
        decision = await decide(client, deps, kind="CURRENCY_AGREEMENT", docId=doc)
        accepted = await invoice(client)
        assert accepted["evidence"]["printedCurrency"] == "IDR"
        assert accepted["total"] == {"amount": inv["total"]["amount"], "currency": "MYR"}
        assert accepted["evidence"]["payment"] == "WAITING_FOR_STATEMENT"
        assert (await month(client))["figures"]["invoicedSales"]["value"] == inv["total"]["amount"]
        await client.delete(f"/api/decisions/{decision['decisionId']}", headers=AUTH)
        await drain(deps)
        assert (await invoice(client))["evidence"]["payment"] == "CURRENCY_TO_CONFIRM"
        assert (await month(client))["figures"]["invoicedSales"]["value"] == "0.00"


async def test_superseded_run_does_not_rewrite_matches_support_evidence_or_findings():
    deps, _ = _deps()
    deps._reader = FakeDocumentReader(_classify, pages=_recorded_page, invoice_pages=_recorded)
    async with _client(deps) as client:
        await _upload(client, deps, STATEMENT, "march.pdf")
        await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")

    async def snapshot():
        return deepcopy(
            (
                await deps.matches.list_matches("org_1"),
                await deps.bank_lines.list_lines("org_1"),
                await deps.invoices.list_records("org_1"),
                await deps.findings.list_findings("org_1"),
            )
        )

    before = await snapshot()
    generation, _ = await deps.month_repo.bump_generation("org_1", "2026-03")
    result = await deps.month_workflow_runner("org_1", "2026-03", generation - 1, "stale_run")
    assert result["status"] == "SUPERSEDED"
    assert await snapshot() == before
