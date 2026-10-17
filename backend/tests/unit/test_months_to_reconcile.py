"""Same data, same result whatever the upload order (constitution 16; docs/08 §6.1): a month's run
looks one month back for the invoices and receipts its payments may settle, so a document that
arrives after the next month was reconciled reconciles that month again. Synthetic data only."""

from app.agents.nodes.doc_nodes import months_to_reconcile
from app.domain.models.document import DocType
from app.domain.models.month import Month
from tests.unit.test_document_workflow import make_doc


class _Deps:
    def __init__(self, month_repo):
        self.month_repo = month_repo


async def test_a_late_invoice_reconciles_the_next_month_when_it_has_a_statement():
    from tests.fakes.month_repository import FakeMonthRepository

    months = FakeMonthRepository()
    await months.save("org_1", Month(month="2026-08", statements=[{"docId": "doc_st_08"}]))
    deps = _Deps(months)

    invoice = make_doc("org_1", "doc_inv", doc_type=DocType.SALES_INVOICE, months=["2026-07"])
    receipt = make_doc("org_1", "doc_rc", doc_type=DocType.RECEIPT, months=["2026-07"])
    statement = make_doc("org_1", "doc_st", doc_type=DocType.BANK_STATEMENT, months=["2026-07"])
    late = make_doc("org_1", "doc_inv2", doc_type=DocType.PURCHASE_INVOICE, months=["2026-08"])

    assert await months_to_reconcile(deps, "org_1", invoice) == ["2026-07", "2026-08"]
    assert await months_to_reconcile(deps, "org_1", receipt) == ["2026-07", "2026-08"]
    assert await months_to_reconcile(deps, "org_1", statement) == ["2026-07"]
    # September has no statement yet: no empty month is made for it.
    assert await months_to_reconcile(deps, "org_1", late) == ["2026-08"]
