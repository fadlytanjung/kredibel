"""Where the money went (spec 010, T010-01, AC-010-5, AC-010-12; docs/08 §5.1). Synthetic data.

The flow is built by code from bank lines and categories.v1.yaml: sources → accounts → activity →
statement line (or → who was paid). Every account balances (Σ in = Σ out + kept), the framework only
moves interest between activities, and IDs do not depend on the order lines arrive in."""

import random
from collections import defaultdict
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.policy_files import load_category_policy
from app.domain.models.bank_line import BankLine
from app.domain.money_flow import MoneyFlow, build_money_flow

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
POLICY = load_category_policy(CONTRACTS / "policy" / "categories.v1.yaml", CONTRACTS / "policy")
ACCOUNTS = {"doc_a": "Archipelago Commerce Bank ••4821", "doc_b": "Harbour Bank ••0912"}
_n = iter(range(10_000))


def line(
    amount: str,
    category: str,
    party: str | None = None,
    doc: str = "doc_a",
    tags: tuple[str, ...] = (),
) -> BankLine:
    i = next(_n)
    return BankLine(
        tx_id=f"tx_{i:04d}",
        doc_id=doc,
        page=1,
        row_index=i,
        date=date(2026, 3, 1 + i % 28),
        month="2026-03",
        description=f"LINE {i}",
        amount=D(amount),
        balance=None,
        counterparty_name=party,
        category=category,
        risk_tags=list(tags),
    )


def flow(lines: list[BankLine], **kw) -> MoneyFlow:
    base = dict(account_of=ACCOUNTS, policy=POLICY, framework="IFRS", view="STATEMENT")
    return build_money_flow(lines, **{**base, **kw})


def links(f: MoneyFlow) -> dict[str, D]:
    return {link.id: link.value for link in f.links}


def node(f: MoneyFlow, node_id: str):
    return next(n for n in f.nodes if n.id == node_id)


def assert_accounts_balance(f: MoneyFlow) -> None:
    into: dict[str, D] = defaultdict(D)
    out: dict[str, D] = defaultdict(D)
    for link in f.links:
        into[link.target] += link.value
        out[link.source] += link.value
    for n in f.nodes:
        if n.column == "ACCOUNT":
            assert into[n.id] == out[n.id], n.label


def test_the_five_largest_clients_then_other_clients_cash_sales_and_other_lines():
    clients = [("Daybreak Cafe", "700"), ("Spice Route", "600"), ("Harborview Hotel", "500"),
               ("Highland Resort", "400"), ("Juniper Bistro", "300"), ("Kettle House", "200"),
               ("Lantern Inn", "100")]  # fmt: skip
    lines = [line(a, "SALES_RECEIPT", p) for p, a in clients]
    lines += [
        line("50.00", "SALES_RECEIPT", tags=("CASH_DEPOSIT",)),
        line("1000", "LOAN_DISBURSEMENT"),
    ]
    f = flow(lines)

    sources = [n for n in f.nodes if n.column == "SOURCE"]
    labels = {n.label: n.value for n in sources}
    assert labels == {
        "Daybreak Cafe": D("700"),
        "Spice Route": D("600"),
        "Harborview Hotel": D("500"),
        "Highland Resort": D("400"),
        "Juniper Bistro": D("300"),
        "Other clients": D("300"),
        "Cash sales deposited": D("50.00"),
        "Loans and owner": D("1000"),
    }
    client = next(n for n in sources if n.label == "Daybreak Cafe")
    account = next(n.id for n in f.nodes if n.column == "ACCOUNT")
    assert client.id.startswith("src:client:cp_") and account.startswith("acc:acc_")
    assert links(f)[f"{client.id}>{account}"] == D("700")
    assert links(f)[f"src:line:FINANCING>{account}"] == D("1000")


def test_debits_go_to_their_activity_then_their_statement_line_split_by_category():
    lines = [
        line("5000", "SALES_RECEIPT", "Daybreak Cafe"),
        line("-800", "INVENTORY_PURCHASE", "Green Valley Farms"),
        line("-200", "RENT"),
        line("-300", "PAYROLL"),
        line("-100", "LOAN_REPAYMENT"),
        line("-400", "ASSET_PURCHASE"),
        line("-25", "UNKNOWN"),
    ]
    got = links(flow(lines))
    assert got["act:OPERATING>line:COST_OF_SALES"] == D("800")
    assert got["act:OPERATING>line:OPERATING_EXPENSES:RENT"] == D("200")
    assert got["act:OPERATING>line:OPERATING_EXPENSES:PAYROLL"] == D("300")
    assert got["act:FINANCING>line:FINANCING:LOAN_REPAYMENT"] == D("100")
    assert got["act:INVESTING>line:INVESTING"] == D("400")
    assert got["act:UNCLASSIFIED>line:NONE:UNKNOWN"] == D("25")
    f = flow(lines)
    assert node(f, "line:COST_OF_SALES").label == "Cost of sales"
    assert node(f, "line:OPERATING_EXPENSES:RENT").label == "Rent"
    assert node(f, "line:NONE:UNKNOWN").label == "Not categorized yet"
    assert node(f, "act:KEPT").value == D("5000") - D("1825")


def test_every_account_balances_with_kept_or_taken_from_balance():
    lines = [
        line("1000", "SALES_RECEIPT", "Daybreak Cafe", doc="doc_a"),
        line("-400", "RENT", doc="doc_a"),
        line("100", "SALES_RECEIPT", "Spice Route", doc="doc_b"),
        line("-300", "PAYROLL", doc="doc_b"),
    ]
    f = flow(lines)
    assert_accounts_balance(f)
    a = next(n.id for n in f.nodes if n.label == ACCOUNTS["doc_a"])
    b = next(n.id for n in f.nodes if n.label == ACCOUNTS["doc_b"])
    assert links(f)[f"{a}>act:KEPT"] == D("600")
    assert links(f)[f"src:balance>{b}"] == D("200")
    assert node(f, "src:balance").label == "Taken from balance"


def test_the_framework_moves_interest_and_renames_lines_but_never_changes_totals():
    lines = [
        line("2000", "SALES_RECEIPT", "Daybreak Cafe"),
        line("-50", "INTEREST_PAID"),
        line("-500", "INVENTORY_PURCHASE"),
    ]
    ifrs, gaap = flow(lines, framework="IFRS"), flow(lines, framework="US_GAAP")
    assert links(ifrs)["act:FINANCING>line:FINANCE_COSTS"] == D("50")
    assert links(gaap)["act:OPERATING>line:FINANCE_COSTS"] == D("50")
    assert node(ifrs, "line:FINANCE_COSTS").label == "Finance costs"
    assert node(gaap, "line:FINANCE_COSTS").label == "Interest expense"
    assert node(gaap, "line:COST_OF_SALES").label == "Cost of goods sold"
    assert ifrs.note == POLICY.framework_notes["IFRS"]
    assert gaap.note == POLICY.framework_notes["US_GAAP"]
    assert ifrs.total == gaap.total == D("2000")
    assert flow([line("10", "SALES_RECEIPT", "A")]).note is None


def test_held_lines_are_left_out_and_totalled():
    lines = [line("1000", "SALES_RECEIPT", "Daybreak Cafe"), line("-300", "RENT", doc="doc_held")]
    f = flow(lines, held_docs=frozenset({"doc_held"}))
    assert f.excluded_held == D("300")
    assert "act:OPERATING>line:OPERATING_EXPENSES:RENT" not in links(f)
    assert_accounts_balance(f)


def test_transfers_are_left_out_unless_shown_and_never_link_two_accounts():
    lines = [
        line("1000", "SALES_RECEIPT", "Daybreak Cafe", doc="doc_a"),
        line("-500", "INTERNAL_TRANSFER", doc="doc_a"),
        line("500", "INTERNAL_TRANSFER", doc="doc_b"),
    ]
    hidden = flow(lines)
    assert not any("own-accounts" in n.id for n in hidden.nodes)
    shown = flow(lines, show_transfers=True)
    a = next(n.id for n in shown.nodes if n.label == ACCOUNTS["doc_a"])
    b = next(n.id for n in shown.nodes if n.label == ACCOUNTS["doc_b"])
    assert links(shown)[f"src:own-accounts>{b}"] == D("500")
    assert links(shown)[f"{a}>act:own-accounts"] == D("500")
    assert node(shown, "src:own-accounts").label == "From own accounts"
    between_accounts = [
        link
        for link in shown.links
        if link.source.startswith("acc:") and link.target.startswith("acc:")
    ]
    assert between_accounts == []
    assert_accounts_balance(hidden)
    assert_accounts_balance(shown)


def test_the_counterparty_view_groups_money_out_by_who_was_paid():
    lines = [
        line("5000", "SALES_RECEIPT", "Daybreak Cafe"),
        line("-800", "INVENTORY_PURCHASE"),
        line("-400", "ASSET_PURCHASE"),
        line("-200", "RENT"),
        line("-100", "UTILITIES"),
        line("-25", "UNKNOWN"),
    ]
    f = flow(lines, view="COUNTERPARTIES")
    assert {n.column for n in f.nodes} == {"SOURCE", "ACCOUNT", "USE"}
    acc = next(n.id for n in f.nodes if n.column == "ACCOUNT")
    got = links(f)
    assert got[f"{acc}>use:SUPPLIERS"] == D("1200")
    assert got[f"{acc}>use:RENT_UTILITIES"] == D("300")
    assert got[f"{acc}>use:UNCATEGORIZED"] == D("25")
    assert got[f"{acc}>use:KEPT"] == D("3475")
    assert node(f, "use:KEPT").label == "Kept in the account"
    assert_accounts_balance(f)


@pytest.mark.parametrize("view", ["STATEMENT", "COUNTERPARTIES"])
def test_the_same_lines_in_any_order_give_the_same_flow(view):
    lines = [
        line("700", "SALES_RECEIPT", "Daybreak Cafe"),
        line("300", "SALES_RECEIPT", "daybreak  cafe", doc="doc_b"),
        line("-200", "RENT"),
        line("-900", "PAYROLL", doc="doc_b"),
        line("40", "INTEREST_RECEIVED"),
    ]
    first = flow(lines, view=view)
    shuffled = lines[:]
    random.Random(7).shuffle(shuffled)
    again = flow(shuffled, view=view)
    assert first.nodes == again.nodes and first.links == again.links
    clients = [n for n in first.nodes if n.id.startswith("src:client:")]
    assert len(clients) == 1 and clients[0].value == D("1000")  # one client, however it is spelled
    assert all(link.id == f"{link.source}>{link.target}" for link in first.links)


def test_each_link_knows_the_lines_behind_it():
    a = line("700", "SALES_RECEIPT", "Daybreak Cafe")
    b = line("300", "SALES_RECEIPT", "Daybreak Cafe")
    f = flow([a, b, line("-100", "RENT")])
    client = next(n.id for n in f.nodes if n.id.startswith("src:client:"))
    behind = next(link for link in f.links if link.source == client)
    assert behind.tx_ids == (a.tx_id, b.tx_id) and behind.line_count == 2
    assert f.lines_of(behind.id) == (a.tx_id, b.tx_id)


_CATEGORIES = sorted(POLICY.categories)


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.integers(min_value=-500_000, max_value=500_000).filter(lambda n: n != 0),
            st.sampled_from(_CATEGORIES),
            st.sampled_from(["doc_a", "doc_b"]),
            st.sampled_from([None, "Daybreak Cafe", "Spice Route", "Harborview Hotel"]),
            st.booleans(),
        ),
        max_size=40,
    ),
    st.booleans(),
)
def test_every_account_balances_and_totals_ignore_the_framework(rows, transfers):
    lines = [
        line(str(D(cents) / 100), category, party, doc=doc, tags=("CASH_DEPOSIT",) if cash else ())
        for cents, category, doc, party, cash in rows
    ]
    totals = set()
    for view in ("STATEMENT", "COUNTERPARTIES"):
        for framework in ("IFRS", "US_GAAP"):
            f = flow(lines, view=view, framework=framework, show_transfers=transfers)
            assert_accounts_balance(f)
            totals.add(f.total)
    assert len(totals) == 1
