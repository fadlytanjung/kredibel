"""A month reconciles itself from its data (spec 007, T007-08, AC-007-14…16, ADR-025).

The synthetic March statement and Daybreak Café's invoice INV/SCR/2026/03/0009, read with recorded
readings: the 19,597,050.00 credit of 21 March pays the invoice automatically with every reason;
the other lines stay bank cash without support; the invoice is paid with bank evidence; the month
has its figures and, with statements covering all of March and nothing to review, is RECONCILED."""

import io

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.reading import DocClassification
from tests.fakes.document_reader import FakeDocumentReader
from tests.integration.test_invoice_workflow import AUTH, PDF, _client, _deps, _recorded
from tests.integration.test_reading_workflow import FIXTURES, _recorded_page

STATEMENT = (FIXTURES / "acb-2026-03.pdf").read_bytes()


def _classify(text: str) -> DocClassification:
    kind = "SALES_INVOICE" if "INVOICE" in text.upper() else "BANK_STATEMENT"
    return DocClassification(doc_type=kind, confidence=0.95)  # type: ignore[arg-type]


async def _upload(client, deps, data: bytes, name: str) -> str:
    res = await client.post(
        "/api/documents", headers=AUTH, files={"file": (name, io.BytesIO(data), "application/pdf")}
    )
    assert res.status_code == 201, res.text
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()
    return res.json()["docId"]


async def test_a_month_with_a_statement_and_an_invoice_reconciles_itself():
    deps, _ = _deps()
    deps._reader = FakeDocumentReader(_classify, pages=_recorded_page, invoice_pages=_recorded)
    async with _client(deps) as client:
        statement = await _upload(client, deps, STATEMENT, "march.pdf")
        invoice_doc = await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")
        [inv] = (
            await client.get("/api/invoices", params={"docId": invoice_doc}, headers=AUTH)
        ).json()["items"]
        lines = (
            await client.get("/api/bank-lines", params={"docId": statement}, headers=AUTH)
        ).json()["items"]
        month = (await client.get("/api/months/2026-03", headers=AUTH)).json()

    [match] = await deps.matches.list_matches("org_1", month="2026-03")
    assert (match.status, match.method, match.kind) == ("CONFIRMED", "AUTO", "BANK_SALES_INVOICE")
    assert match.reasons == ["AMOUNT_EXACT", "PARTY_MATCH", "REFERENCE_IN_TEXT", "DATE_NEAR"]
    assert match.invoice_ids == [inv["invoiceId"]]

    assert inv["evidence"]["payment"] == "PAID_BANK"
    assert inv["evidence"]["bankPaid"] == {"amount": "19597050.00", "currency": "IDR"}
    assert inv["evidence"]["matchIds"] == [match.match_id]

    paid = next(ln for ln in lines if ln["txId"] in match.bank_line_ids)
    assert (paid["support"], paid["match"]["state"]) == ("MATCHED", "AUTO")
    others = {ln["support"] for ln in lines if ln["txId"] not in match.bank_line_ids}
    assert others <= {"NO_SUPPORT", "EXCLUDED"} and "NO_SUPPORT" in others

    figures = month["figures"]
    assert figures["autoMatched"]["value"] == "1" and figures["bankLines"]["value"] == str(
        len(lines)
    )
    assert figures["moneyIn"]["factId"] == "fact:2026-03:money_in"
    assert month["state"] == "RECONCILED" and month.get("note") is None
