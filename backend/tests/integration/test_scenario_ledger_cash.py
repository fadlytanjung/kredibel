"""Bank lines booked in the ledger (docs/08 §6.2, ledger cash) on S1 through the month runs: every
automatic bank-to-ledger match is one the scenario's truth lists, most lines no document explains
are matched to their booking, and the risk checks still see only document matches. Synthetic data
only."""

from decimal import Decimal

from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client


async def test_s1_bank_lines_are_matched_to_their_bookings_as_the_truth_says():
    truth = books.load_truth("S1")
    # Lines a document explains are matched to the document; the ledger pass takes the others.
    by_document = {b for m in truth["matches"] if m["documents"] for b in m["bank"]}
    expected = {
        (tuple(m["bank"]), tuple(m["ledger"]))
        for m in truth["matches"]
        if m["kind"] == "BANK_LEDGER" and not set(m["bank"]) & by_document
    }
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        rates = {}
        found = set()
        for month in books.MONTHS:
            body = (await client.get(f"/api/months/{month}", headers=AUTH)).json()
            rates[month] = Decimal(body["figures"]["autoMatchRate"]["value"])
            res = await client.get("/api/matches", params={"month": month}, headers=AUTH)
            for m in res.json()["items"]:
                if m["kind"] == "BANK_LEDGER":
                    assert (m["method"], m["status"]) == ("AUTO", "CONFIRMED")
                    assert "LEDGER_BOOKED" in m["reasons"]
                    found.add((tuple(m["bankLineIds"]), tuple(m["ledgerEntryIds"])))

    assert found <= expected, sorted(found - expected)  # never a wrong automatic match
    assert len(found) >= 0.9 * len(expected)
    # "Matched by Kredibel": a month whose ledger books its bank account is mostly matched.
    assert all(rate >= Decimal("0.85") for rate in rates.values()), rates


async def test_s1_cash_deposits_take_the_category_their_booking_names():
    """AC-023-12: "CASH DEPOSIT" does not say whose money it is; the ledger books it to sales, so
    the matched line is a sales receipt, from its match."""
    from datetime import UTC, datetime

    from app.domain.models.events import AuditEvent
    from app.domain.profit_loss import Classification
    from scripts.upload_demo_books import DEFAULT_CLASSIFICATIONS

    deps = books.books_deps()
    await books.seed(deps, "S1", books.load_truth("S1"))
    for code, (pnl_line, subledger) in DEFAULT_CLASSIFICATIONS.items():
        event = AuditEvent(
            event_id=f"evt_{code}",
            type="ACCOUNT_CLASSIFIED",
            actor_uid="u_1",
            actor_role="owner",
            at=datetime(2026, 7, 1, tzinfo=UTC),
            subject={"accountCode": code},
            details={},
        )
        await deps.ledger_repo.confirm(
            books.ORG,
            Classification(account_code=code, pnl_line=pnl_line, subledger=subledger),
            event,
        )
    # As the reading leaves a deposit that names nobody (the demo's statements).
    for line in await deps.bank_lines.list_lines(books.ORG, limit=5000):
        if "CASH DEPOSIT" in line.description.upper():
            line.category, line.categorized_by, line.cashflow_class = (
                "UNKNOWN",
                "NONE",
                "UNCLASSIFIED",
            )
    await books.run_months(deps)

    lines = await deps.bank_lines.list_lines(books.ORG, limit=5000)
    deposits = [ln for ln in lines if "CASH DEPOSIT" in ln.description.upper()]
    matched = [ln for ln in deposits if ln.match_state == "AUTO"]
    assert matched, "S1 has cash deposits its ledger books"
    assert {(ln.category, ln.categorized_by) for ln in matched} == {("SALES_RECEIPT", "MATCH")}
    assert all(ln.cashflow_class == "OPERATING" for ln in matched)
