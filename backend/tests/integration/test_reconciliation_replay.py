"""Generated invoices and cash/card receipts through the full HTTP → workflow path."""

from decimal import Decimal

from tests.integration.test_document_first_reconciliation import decide
from tests.integration.test_invoice_workflow import AUTH, _client
from tests.integration.test_month_workflow_reconcile import _upload
from tests.support.reconciliation_demo import DOCUMENTS, FIXTURES, demo_deps


async def replay(*, statement_first: bool):
    deps = demo_deps()
    ordered = sorted(
        DOCUMENTS,
        key=lambda d: (
            (d["docType"] == "BANK_STATEMENT") != statement_first,
            d["file"],
        ),
    )
    async with _client(deps) as client:
        for document in ordered:
            doc_id = await _upload(
                client, deps, (FIXTURES / document["file"]).read_bytes(), document["file"]
            )
            stored = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()
            assert stored["status"] == "DONE", stored.get("statusDetail")
            assert not stored.get("heldAsDuplicate"), (document["file"], stored.get("duplicate"))
            if document["docType"] == "RECEIPT":
                # Neither till roll prints a currency. The user agrees to the fixed workspace
                # currency, keeping the amounts unchanged; nothing infers or converts it.
                await decide(client, deps, kind="CURRENCY_AGREEMENT", docId=doc_id)
        invoices = (await client.get("/api/invoices", headers=AUTH)).json()["items"]
        receipts = (await client.get("/api/receipts", headers=AUTH)).json()["items"]
        month = (await client.get("/api/months/2026-03", headers=AUTH)).json()
        lines = (await client.get("/api/bank-lines", headers=AUTH)).json()["items"]

    assert {i["kind"] for i in invoices} == {"SALES", "PURCHASE"}
    assert all(i["evidence"]["payment"] == "PAID_BANK" for i in invoices)
    cash = next(r for r in receipts if r["paymentMethod"] == "CASH")
    card = next(r for r in receipts if r["paymentMethod"] == "CARD")
    assert cash["evidence"] is not None, (cash["date"], cash["total"], cash["notes"])
    assert card["evidence"] is not None, card
    assert cash["evidence"]["payment"] == "PAID_CASH"
    assert cash["evidence"]["bankPaid"]["amount"] == "0.00"
    assert card["evidence"]["payment"] == "PAID_BANK"
    assert len(await deps.matches.list_matches("org_1")) == 3
    bank = next(d for d in DOCUMENTS if d["docType"] == "BANK_STATEMENT")
    incoming = sum((Decimal(r["credit"] or "0") for r in bank["rows"]), Decimal(0))
    assert Decimal(month["figures"]["moneyIn"]["value"]) == incoming
    assert any(ln["support"] == "NO_SUPPORT" for ln in lines)
    assert any(ln["categorizedBy"] == "RULE" for ln in lines)
    summary = {
        "invoices": sorted((i["number"], i["total"], i["evidence"]["payment"]) for i in invoices),
        "receipts": sorted((r["number"], r["total"], r["evidence"]["payment"]) for r in receipts),
        "figures": {k: v["value"] for k, v in month["figures"].items()},
        "state": month["state"],
    }
    return summary, deps


async def test_generated_documents_reconcile_in_either_upload_order():
    first, _ = await replay(statement_first=True)
    last, _ = await replay(statement_first=False)
    assert first == last
