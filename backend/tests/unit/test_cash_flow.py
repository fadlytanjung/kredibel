"""Money in and out by month, and the cash-flow statement (spec 010, T010-01b, AC-010-13, AC-010-14;
docs/08 §5.2). Synthetic data.

opening + Σ activities = closing is checked in code; when it does not hold, the result says why
(a missing month, no printed balances, a balance break, transfers to an account without
statements) instead of drawing a balance that does not exist."""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.policy_files import load_category_policy
from app.domain.cash_flow import CashFlow, build_cash_flow
from app.domain.models.bank_line import BankLine

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
POLICY = load_category_policy(CONTRACTS / "policy" / "categories.v1.yaml", CONTRACTS / "policy")
ACCOUNTS = {"doc_a": "Archipelago Commerce Bank ••4821", "doc_b": "Harbour Bank ••0912"}


class Statement:
    """Lines of one account with running balances, as a statement prints them."""

    def __init__(self, doc: str, opening: str) -> None:
        self.doc, self.balance, self.lines, self.row = doc, D(opening), [], 0

    def add(self, day: date, amount: str, category: str, *, printed: bool = True) -> "Statement":
        self.balance += D(amount)
        self.row += 1
        self.lines.append(
            BankLine(
                tx_id=f"{self.doc}_{self.row:03d}",
                doc_id=self.doc,
                page=1,
                row_index=self.row,
                date=day,
                month=f"{day:%Y-%m}",
                description=f"LINE {self.row}",
                amount=D(amount),
                balance=self.balance if printed else None,
                category=category,
            )
        )
        return self


def cash(lines: list[BankLine], months: list[str], **kw) -> CashFlow:
    base = dict(account_of=ACCOUNTS, policy=POLICY, framework="IFRS")
    return build_cash_flow(lines, months=months, **{**base, **kw})


def test_money_in_and_out_by_month_with_the_month_end_balance_and_risk():
    a = (
        Statement("doc_a", "1000")
        .add(date(2026, 1, 5), "500", "SALES_RECEIPT")
        .add(date(2026, 1, 9), "-200", "RENT")
        .add(date(2026, 2, 3), "300", "SALES_RECEIPT")
        .add(date(2026, 2, 7), "-700", "PAYROLL")
    )
    f = cash(a.lines, ["2026-01", "2026-02"], risk={"2026-02": "HIGH"})
    jan, feb = f.months
    assert (jan.month, jan.money_in, jan.money_out, jan.net, jan.closing) == (
        "2026-01",
        D("500"),
        D("200"),
        D("300"),
        D("1300"),
    )
    assert (feb.net, feb.closing, feb.risk_level, jan.risk_level) == (
        D("-400"),
        D("900"),
        "HIGH",
        None,
    )
    assert (f.opening, f.closing, f.balanced, f.gaps) == (D("1000"), D("900"), True, ())


def test_activities_and_lines_follow_the_framework_and_always_add_up():
    a = (
        Statement("doc_a", "2000")
        .add(date(2026, 3, 2), "1500", "SALES_RECEIPT")
        .add(date(2026, 3, 3), "-300", "RENT")
        .add(date(2026, 3, 4), "-50", "INTEREST_PAID")
        .add(date(2026, 3, 5), "-400", "ASSET_PURCHASE")
        .add(date(2026, 3, 6), "-100", "LOAN_REPAYMENT")
        .add(date(2026, 3, 7), "-25", "UNKNOWN")
    )
    ifrs = cash(a.lines, ["2026-03"], framework="IFRS")
    gaap = cash(a.lines, ["2026-03"], framework="US_GAAP")
    assert ifrs.by_activity == {
        "OPERATING": D("1200"),
        "INVESTING": D("-400"),
        "FINANCING": D("-150"),
        "UNCLASSIFIED": D("-25"),
    }
    assert gaap.by_activity["OPERATING"] == D("1150") and gaap.by_activity["FINANCING"] == D("-100")
    for f in (ifrs, gaap):
        assert f.opening is not None and f.balanced
        assert f.opening + sum(f.by_activity.values()) == f.closing
    lines = {(x.line, x.category): (x.label, x.cashflow_class, x.amount) for x in ifrs.by_line}
    assert lines[("REVENUE", None)] == ("Revenue", "OPERATING", D("1500"))
    assert lines[("OPERATING_EXPENSES", "RENT")] == ("Rent", "OPERATING", D("-300"))
    assert lines[("FINANCE_COSTS", None)] == ("Finance costs", "FINANCING", D("-50"))
    assert lines[("NONE", "UNKNOWN")] == ("Not categorized yet", "UNCLASSIFIED", D("-25"))
    gaap_lines = {(x.line, x.category): x for x in gaap.by_line}
    assert gaap_lines[("FINANCE_COSTS", None)].label == "Interest expense"
    assert gaap_lines[("FINANCE_COSTS", None)].cashflow_class == "OPERATING"
    assert ifrs.note == POLICY.framework_notes["IFRS"]
    assert [x.line for x in ifrs.by_line] == sorted(
        (x.line for x in ifrs.by_line), key=lambda line: POLICY.lines[line].order
    )


def test_a_month_without_a_statement_between_two_others_is_a_gap():
    a = Statement("doc_a", "1000").add(date(2026, 1, 5), "500", "SALES_RECEIPT")
    a.add(date(2026, 2, 5), "-300", "RENT")  # February's statement was never uploaded
    february = a.lines.pop()
    a.add(date(2026, 3, 5), "200", "SALES_RECEIPT")
    f = cash(a.lines, ["2026-01", "2026-02", "2026-03"])
    kinds = {(g.kind, g.month, g.account) for g in f.gaps}
    assert ("MISSING_MONTH", "2026-02", ACCOUNTS["doc_a"]) in kinds
    breaks = [g for g in f.gaps if g.kind == "BALANCE_BREAK"]
    assert breaks and breaks[0].amount == abs(february.amount)
    assert not f.balanced


def test_lines_without_balances_and_transfers_to_an_account_without_statements_are_gaps():
    a = (
        Statement("doc_a", "1000")
        .add(date(2026, 3, 2), "800", "SALES_RECEIPT")
        .add(date(2026, 3, 9), "-500", "INTERNAL_TRANSFER")
    )
    b = Statement("doc_b", "0").add(date(2026, 3, 4), "100", "SALES_RECEIPT", printed=False)
    f = cash(a.lines + b.lines, ["2026-03"])
    gaps = {g.kind: g for g in f.gaps}
    assert gaps["NO_BALANCES"].account == ACCOUNTS["doc_b"]
    assert gaps["TRANSFERS_ELSEWHERE"].amount == D("-500")
    assert not f.balanced

    # Both sides of a transfer between own accounts with statements cancel out.
    c = Statement("doc_b", "0").add(date(2026, 3, 9), "500", "INTERNAL_TRANSFER")
    both = cash(a.lines + c.lines, ["2026-03"])
    assert both.balanced and both.gaps == ()
    assert both.opening == D("1000") and both.closing == D("1800")


def test_held_lines_are_left_out():
    a = Statement("doc_a", "1000").add(date(2026, 3, 2), "800", "SALES_RECEIPT")
    held = Statement("doc_h", "0").add(date(2026, 3, 2), "800", "SALES_RECEIPT")
    f = cash(a.lines + held.lines, ["2026-03"], held_docs=frozenset({"doc_h"}))
    assert f.months[0].money_in == D("800") and f.closing == D("1800") and f.balanced


_CASH = sorted(
    c for c, cat in POLICY.categories.items() if cat.cashflow_class("IFRS") != "NON_CASH"
)


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.sampled_from(["doc_a", "doc_b"]),
            st.integers(min_value=0, max_value=89),
            st.integers(min_value=-90_000, max_value=90_000).filter(lambda n: n != 0),
            st.sampled_from(_CASH),
        ),
        min_size=1,
        max_size=30,
    )
)
def test_consistent_statements_always_add_up_in_both_frameworks(rows):
    statements = {"doc_a": Statement("doc_a", "5000"), "doc_b": Statement("doc_b", "100")}
    for doc, day, cents, category in sorted(rows, key=lambda r: (r[0], r[1])):
        statements[doc].add(date(2026, 1, 1) + timedelta(days=day), str(D(cents) / 100), category)
    lines = [ln for statement in statements.values() for ln in statement.lines]
    for framework in ("IFRS", "US_GAAP"):
        f = cash(lines, ["2026-01", "2026-02", "2026-03"], framework=framework)
        assert {g.kind for g in f.gaps} <= {"MISSING_MONTH"}
        if f.balanced:
            assert f.opening is not None and f.closing is not None
            assert f.opening + sum(f.by_activity.values()) == f.closing
