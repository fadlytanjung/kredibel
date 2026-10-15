"""Month checks (docs/08 §2.2 D07, §2.6, §2.7): statement continuity and coverage, behaviour, double
payments, overdue and unknown-party invoices, changed supplier accounts. Pure; the caller passes the
month's eligible lines, all statements and invoices, and the month's bank-to-document allocations.

X09 (ledger against bank) waits for ledger import.
"""

import calendar
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from rapidfuzz import fuzz

from app.domain.findings import Evidence, Finding, Severity, finding_id
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt
from app.domain.profit_loss import LedgerRow
from app.domain.reconcile import Allocation
from app.domain.reconciliation_policy import ReconciliationPolicy

from .policy import ForensicsPolicy


@dataclass(frozen=True)
class StatementSpan:
    doc_id: str
    account: str  # bank and masked number: the same account across statements
    start: date
    end: date
    opening: Decimal | None
    closing: Decimal | None


@dataclass
class MonthContext:
    month: str  # yyyy-mm
    policy: ForensicsPolicy
    reconciliation: ReconciliationPolicy
    workspace_currency: str
    statements: list[StatementSpan]  # every eligible statement of the workspace
    lines: list[BankLine]  # the month's eligible lines
    all_lines: list[BankLine]  # every eligible line: who the business has paid before
    invoices: list[Invoice]  # every invoice: history for X08, overdue ones for R01
    receipts: list[Receipt]
    allocations: list[Allocation]  # the month's bank-to-document allocations
    negative_days: int
    own_names: list[str] = field(default_factory=list)
    ledger_rows: list[LedgerRow] = field(default_factory=list)
    bank_account_mappings: dict[str, str] = field(default_factory=dict)

    @property
    def first_day(self) -> date:
        year, month = map(int, self.month.split("-"))
        return date(year, month, 1)

    @property
    def last_day(self) -> date:
        first = self.first_day
        return first.replace(day=calendar.monthrange(first.year, first.month)[1])

    def finding(
        self,
        code: str,
        anchor: str,
        *,
        category: str,
        severity: Severity,
        title: str,
        facts: dict[str, str],
        evidence: list[Evidence],
    ) -> Finding:
        return Finding(
            finding_id=finding_id(code, f"{self.month}|{anchor}"),
            code=code,
            category=category,  # type: ignore[arg-type]
            severity=severity,
            title=title,
            facts=facts,
            evidence=evidence,
            scope="MONTH",
            month=self.month,
            next_steps=[s] if (s := self.policy.next_steps.get(code)) else [],
        )


MonthCheck = Callable[[MonthContext], list[Finding]]
_CHECKS: dict[str, MonthCheck] = {}


def _check(code: str) -> Callable[[MonthCheck], MonthCheck]:
    def register(fn: MonthCheck) -> MonthCheck:
        _CHECKS[code] = fn
        return fn

    return register


def run_month_checks(ctx: MonthContext) -> list[Finding]:
    out: list[Finding] = []
    for code, run in sorted(_CHECKS.items()):
        if code in ctx.policy.enabled:
            out += run(ctx)
    return sorted(out, key=lambda f: (f.severity_rank, f.code, f.finding_id))


# ---------------------------------------------------------------------------- helpers


def _fold(text: str | None) -> str:
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[^\W_]+", text.upper()))


def _same_party(a: str | None, b: str | None, min_score: float) -> bool:
    fa, fb = _fold(a), _fold(b)
    return bool(fa and fb) and fuzz.token_set_ratio(fa, fb) >= min_score


def _line_party(line: BankLine) -> str:
    return line.counterparty_name or line.description


def _line_evidence(line: BankLine, label: str) -> Evidence:
    c = line.consensus.get("amount", {})
    return Evidence(
        doc_id=line.doc_id,
        page=c.get("page") or line.page,
        bbox=c.get("bbox"),
        tx_id=line.tx_id,
        label=label,
    )


def _money(v: Decimal) -> str:
    return f"{v:.2f}"


def _month_of(day: date) -> str:
    return f"{day:%Y-%m}"


def _confirmed_documents(ctx: MonthContext) -> set[str]:
    return {r for a in ctx.allocations if a.status == "CONFIRMED" for r in a.right_ids}


def _covered(ctx: MonthContext, start: date, end: date) -> bool:
    """Every day from start to end is inside some statement's period."""
    day = start
    spans = sorted(ctx.statements, key=lambda s: s.start)
    for s in spans:
        if s.start > day:
            break
        if s.end >= day:
            day = s.end + timedelta(days=1)
        if day > end:
            return True
    return day > end


# ---------------------------------------------------------------------------- statements


def _by_account(ctx: MonthContext) -> dict[str, list[StatementSpan]]:
    out: dict[str, list[StatementSpan]] = {}
    for s in ctx.statements:
        out.setdefault(s.account, []).append(s)
    return {k: sorted(v, key=lambda s: (s.start, s.doc_id)) for k, v in out.items()}


@_check("X01_STATEMENT_DISCONTINUITY")
def statement_discontinuity(ctx: MonthContext) -> list[Finding]:
    tol = Decimal(ctx.policy.cross_document.continuity_tolerance_minor) / 100
    out: list[Finding] = []
    for account, spans in _by_account(ctx).items():
        for before, after in zip(spans, spans[1:], strict=False):
            adjacent = after.start == before.end + timedelta(days=1)
            if not adjacent or _month_of(after.start) != ctx.month:
                continue
            if before.closing is None or after.opening is None:
                continue
            if abs(before.closing - after.opening) <= tol:
                continue
            out.append(
                ctx.finding(
                    "X01_STATEMENT_DISCONTINUITY",
                    f"{before.doc_id}|{after.doc_id}",
                    category="CROSS_DOCUMENT",
                    severity="HIGH",
                    title="This statement does not open with the last statement's closing balance",
                    facts={
                        "account": account,
                        "previousClosing": _money(before.closing),
                        "opening": _money(after.opening),
                        "difference": _money(after.opening - before.closing),
                    },
                    evidence=[
                        Evidence(doc_id=before.doc_id, page=1, label="Closing balance"),
                        Evidence(doc_id=after.doc_id, page=1, label="Opening balance"),
                    ],
                )
            )
    return out


@_check("X02_STATEMENT_MISSING")
def statement_missing(ctx: MonthContext) -> list[Finding]:
    out: list[Finding] = []
    for account, spans in _by_account(ctx).items():
        first, last = _month_of(spans[0].start), _month_of(spans[-1].end)
        if not first < ctx.month < last:
            continue
        if any(s.start <= ctx.last_day and s.end >= ctx.first_day for s in spans):
            continue
        out.append(
            ctx.finding(
                "X02_STATEMENT_MISSING",
                account,
                category="CROSS_DOCUMENT",
                severity="MEDIUM",
                title="No statement covers this month for an account that has statements around it",
                facts={"account": account, "month": ctx.month},
                evidence=[Evidence(doc_id=spans[0].doc_id, page=1, label="Earlier statement")],
            )
        )
    return out


# ---------------------------------------------------------------------------- behaviour


def _tagged(ctx: MonthContext, tag: str) -> list[BankLine]:
    return sorted(
        (ln for ln in ctx.lines if tag in ln.risk_tags), key=lambda ln: (ln.date, ln.tx_id)
    )


@_check("B01_GAMBLING_INDICATORS")
def gambling(ctx: MonthContext) -> list[Finding]:
    lines = _tagged(ctx, "GAMBLING")
    if len(lines) < ctx.policy.behaviour.gambling_min_count:
        return []
    total = -sum((ln.amount for ln in lines), Decimal(0))
    return [
        ctx.finding(
            "B01_GAMBLING_INDICATORS",
            "gambling",
            category="BEHAVIOURAL",
            severity="MEDIUM",
            title="Payments to gambling sites this month",
            facts={"count": str(len(lines)), "total": _money(total)},
            evidence=[_line_evidence(ln, "Gambling payment") for ln in lines[:10]],
        )
    ]


@_check("B04_RETURNED_ITEMS")
def returned_items(ctx: MonthContext) -> list[Finding]:
    lines = _tagged(ctx, "RETURNED_ITEM")
    behaviour = ctx.policy.behaviour
    if len(lines) < behaviour.returned_items_medium:
        return []
    severity: Severity = "HIGH" if len(lines) >= behaviour.returned_items_high else "MEDIUM"
    return [
        ctx.finding(
            "B04_RETURNED_ITEMS",
            "returned",
            category="BEHAVIOURAL",
            severity=severity,
            title="Payments came back this month",
            facts={"count": str(len(lines))},
            evidence=[_line_evidence(ln, "Returned payment") for ln in lines[:10]],
        )
    ]


@_check("C02_NEGATIVE_BALANCE_DAYS")
def negative_days(ctx: MonthContext) -> list[Finding]:
    if ctx.negative_days < ctx.policy.behaviour.negative_days_threshold:
        return []
    return [
        ctx.finding(
            "C02_NEGATIVE_BALANCE_DAYS",
            "negative",
            category="BEHAVIOURAL",
            severity="MEDIUM",
            title="The account was below zero on several days",
            facts={"days": str(ctx.negative_days)},
            evidence=[],
        )
    ]


# ---------------------------------------------------------------------------- payments


def _due(doc: Invoice, ctx: MonthContext) -> date:
    assert doc.issue_date is not None
    terms = timedelta(days=ctx.reconciliation.windows.default_terms_days)
    return doc.due_date or doc.issue_date + terms


@_check("D07_DOUBLE_PAYMENT")
def double_payment(ctx: MonthContext) -> list[Finding]:
    """A purchase invoice paid by one debit, and another debit of the same amount to the same party
    in its payment window that nothing else explains."""
    docs = {i.invoice_id: i for i in ctx.invoices if i.kind == "PURCHASE"}
    explained = {tx for a in ctx.allocations if a.status == "CONFIRMED" for tx in a.left_ids}
    lines = {ln.tx_id: ln for ln in ctx.lines}
    windows = ctx.reconciliation.windows
    party_min = float(ctx.reconciliation.thresholds.party_min_score_for_split) * 100
    out: list[Finding] = []
    for a in ctx.allocations:
        if a.status != "CONFIRMED" or len(a.left_ids) != 1 or len(a.right_ids) != 1:
            continue
        doc = docs.get(a.right_ids[0])
        if doc is None or doc.total is None or doc.issue_date is None:
            continue
        tolerance = ctx.reconciliation.tolerance(doc.total, ctx.workspace_currency)
        if tolerance is None:
            continue
        earliest = doc.issue_date - timedelta(days=windows.invoice_before_issue_days)
        latest = _due(doc, ctx) + timedelta(days=windows.grace_days)
        for line in sorted(lines.values(), key=lambda ln: (ln.date, ln.tx_id)):
            if line.tx_id in explained or line.amount >= 0:
                continue
            if abs(abs(line.amount) - doc.total) > tolerance:
                continue
            if not earliest <= line.date <= latest:
                continue
            if not _same_party(doc.issuer_name, _line_party(line), party_min):
                continue
            first = lines.get(a.left_ids[0])
            evidence = [_line_evidence(line, "Second payment")]
            if first is not None:
                evidence.insert(0, _line_evidence(first, "First payment"))
            out.append(
                ctx.finding(
                    "D07_DOUBLE_PAYMENT",
                    f"{doc.invoice_id}|{line.tx_id}",
                    category="DUPLICATE",
                    severity="HIGH",
                    title="An invoice that is already paid seems to have been paid again",
                    facts={
                        "invoice": doc.number or doc.invoice_id,
                        "supplier": doc.issuer_name or "",
                        "amount": _money(doc.total),
                        "firstPayment": a.left_ids[0],
                        "secondPayment": line.tx_id,
                    },
                    evidence=evidence,
                )
            )
    return out


@_check("R01_SALES_INVOICE_OVERDUE")
def overdue_sales(ctx: MonthContext) -> list[Finding]:
    """Unpaid more than graceDays after its due date, and statements cover the whole time it could
    have been paid in: without coverage the invoice is waiting for a statement, not overdue."""
    paid = _confirmed_documents(ctx)
    # A proposed payment (a net-of-tax shortfall, a close candidate) waits for the person.
    asked = {r for a in ctx.allocations if a.status == "PROPOSED" for r in a.right_ids}
    grace = timedelta(days=ctx.policy.reconciliation_checks.overdue_grace_days)
    share = ctx.policy.reconciliation_checks.overdue_medium_share
    out: list[Finding] = []
    for inv in ctx.invoices:
        if inv.kind != "SALES" or inv.invoice_id in paid | asked or inv.total is None:
            continue
        if inv.issue_date is None:
            continue
        overdue_on = _due(inv, ctx) + grace
        if _month_of(overdue_on) != ctx.month or not _covered(ctx, inv.issue_date, overdue_on):
            continue
        month_sales = sum(
            (
                i.total
                for i in ctx.invoices
                if i.kind == "SALES" and i.month == inv.month and i.total is not None
            ),
            Decimal(0),
        )
        severity: Severity = "MEDIUM" if inv.total > share * month_sales else "LOW"
        c = inv.consensus.get("total", {})
        out.append(
            ctx.finding(
                "R01_SALES_INVOICE_OVERDUE",
                inv.invoice_id,
                category="RECONCILIATION",
                severity=severity,
                title="A sales invoice is still unpaid well after its due date",
                facts={
                    "invoice": inv.number or inv.invoice_id,
                    "client": inv.buyer_name or "",
                    "total": _money(inv.total),
                    "dueDate": _due(inv, ctx).isoformat(),
                    "overdueSince": overdue_on.isoformat(),
                },
                evidence=[
                    Evidence(
                        doc_id=inv.doc_id,
                        page=c.get("page"),
                        bbox=c.get("bbox"),
                        invoice_id=inv.invoice_id,
                        label="Invoice total",
                    )
                ],
            )
        )
    return out


@_check("R02_SUPPLIER_INVOICE_UNKNOWN_PARTY")
def unknown_supplier(ctx: MonthContext) -> list[Finding]:
    """A purchase invoice from a supplier the business has never paid, not paid now either."""
    paid = _confirmed_documents(ctx)
    party_min = float(ctx.reconciliation.thresholds.party_min_score_for_split) * 100
    out: list[Finding] = []
    for inv in ctx.invoices:
        if inv.kind != "PURCHASE" or inv.month != ctx.month or inv.invoice_id in paid:
            continue
        if any(_same_party(inv.issuer_name, _line_party(ln), party_min) for ln in ctx.all_lines):
            continue
        c = inv.consensus.get("issuerName", {})
        out.append(
            ctx.finding(
                "R02_SUPPLIER_INVOICE_UNKNOWN_PARTY",
                inv.invoice_id,
                category="RECONCILIATION",
                severity="MEDIUM",
                title="An invoice from a supplier this business has never paid",
                facts={
                    "invoice": inv.number or inv.invoice_id,
                    "supplier": inv.issuer_name or "",
                    "total": _money(inv.total) if inv.total is not None else "",
                },
                evidence=[
                    Evidence(
                        doc_id=inv.doc_id,
                        page=c.get("page"),
                        bbox=c.get("bbox"),
                        invoice_id=inv.invoice_id,
                        label="Supplier",
                    )
                ],
            )
        )
    return out


@_check("X08_SUPPLIER_ACCOUNT_CHANGED")
def supplier_account_changed(ctx: MonthContext) -> list[Finding]:
    """A purchase invoice asks to be paid into an account this supplier never used before."""
    purchases = sorted(
        (i for i in ctx.invoices if i.kind == "PURCHASE" and i.issue_date and i.pay_to_masked),
        key=lambda i: (i.issue_date, i.invoice_id),
    )
    out: list[Finding] = []
    for inv in purchases:
        if inv.month != ctx.month:
            continue
        earlier = [
            e
            for e in purchases
            if e.issue_date < inv.issue_date  # type: ignore[operator]
            and _same_party(e.issuer_name, inv.issuer_name, 90)
        ]
        seen = {e.pay_to_masked for e in earlier}
        if not seen or inv.pay_to_masked in seen:
            continue
        c = inv.consensus.get("payTo", {})
        out.append(
            ctx.finding(
                "X08_SUPPLIER_ACCOUNT_CHANGED",
                inv.invoice_id,
                category="CROSS_DOCUMENT",
                severity="HIGH",
                title="A supplier asks to be paid into a new bank account",
                facts={
                    "supplier": inv.issuer_name or "",
                    "earlierAccount": earlier[-1].pay_to_masked or "",
                    "newAccount": inv.pay_to_masked or "",
                    "invoice": inv.number or inv.invoice_id,
                },
                evidence=[
                    Evidence(doc_id=earlier[-1].doc_id, page=1, label="Earlier account"),
                    Evidence(
                        doc_id=inv.doc_id,
                        page=c.get("page"),
                        bbox=c.get("bbox"),
                        invoice_id=inv.invoice_id,
                        label="New account",
                    ),
                ],
            )
        )
    return out


@_check("X09_LEDGER_BANK_MISMATCH")
def ledger_bank_mismatch(ctx: MonthContext) -> list[Finding]:
    """docs/08 §2.6: For a mapped bank account, ledger cash movement for the month differs from
    the statement's net movement by > tol; or a ledger cash entry has no bank line within the
    window."""
    if not ctx.bank_account_mappings:
        return []

    tol = Decimal(ctx.policy.cross_document.continuity_tolerance_minor) / 100
    high_threshold = ctx.policy.cross_document.ledger_month_difference_high
    ledger_days = ctx.reconciliation.windows.ledger_days
    out: list[Finding] = []

    for account, ledger_code in sorted(ctx.bank_account_mappings.items()):
        account_spans = [s for s in ctx.statements if s.account == account]
        doc_ids = {s.doc_id for s in account_spans}
        month_lines = [
            ln for ln in ctx.lines if ln.doc_id in doc_ids and ln.cashflow_class != "NON_CASH"
        ]
        all_account_lines = [
            ln for ln in ctx.all_lines if ln.doc_id in doc_ids and ln.cashflow_class != "NON_CASH"
        ] or month_lines

        month_rows = [
            r
            for r in ctx.ledger_rows
            if r.account_code == ledger_code
            and not r.held_as_duplicate
            and _month_of(r.date) == ctx.month
        ]
        if not account_spans and not month_rows:
            continue

        bank_net = sum((ln.amount for ln in month_lines), Decimal(0))
        # In a bank/cash asset account, debits increase cash and credits decrease cash:
        ledger_net = sum((r.debit - r.credit for r in month_rows), Decimal(0))
        diff = abs(ledger_net - bank_net)

        if diff > tol:
            is_high = (diff / abs(bank_net) > high_threshold) if bank_net != Decimal(0) else True
            severity: Severity = "HIGH" if is_high else "MEDIUM"
            ev: list[Evidence] = []
            if account_spans:
                ev.append(Evidence(doc_id=account_spans[0].doc_id, page=1, label="Bank statement"))
            for r in month_rows[:5]:
                ev.append(
                    Evidence(doc_id=r.doc_id, ledger_entry_id=r.entry_id, label="Ledger entry")
                )
            out.append(
                ctx.finding(
                    "X09_LEDGER_BANK_MISMATCH",
                    f"{account}|month_difference",
                    category="CROSS_DOCUMENT",
                    severity=severity,
                    title="Ledger cash movement for this month does not match bank statements",
                    facts={
                        "account": account,
                        "ledgerAccountCode": ledger_code,
                        "ledgerMovement": _money(ledger_net),
                        "bankMovement": _money(bank_net),
                        "difference": _money(diff),
                    },
                    evidence=ev,
                )
            )

        # Per entry check:
        for row in sorted(month_rows, key=lambda r: (r.date, r.entry_id)):
            row_amount = row.debit - row.credit
            if row_amount == Decimal(0):
                continue
            tolerance = ctx.reconciliation.tolerance(abs(row_amount), ctx.workspace_currency)
            if tolerance is None:
                tolerance = tol
            candidates = [
                ln
                for ln in all_account_lines
                if abs((ln.date - row.date).days) <= ledger_days
                and ln.amount * row_amount > 0
                and abs(abs(ln.amount) - abs(row_amount)) <= tolerance
            ]
            if not candidates:
                out.append(
                    ctx.finding(
                        "X09_LEDGER_BANK_MISMATCH",
                        f"{row.doc_id}|{row.entry_id}",
                        category="CROSS_DOCUMENT",
                        severity="MEDIUM",
                        title="A ledger cash entry has no corresponding bank line",
                        facts={
                            "account": account,
                            "ledgerAccountCode": ledger_code,
                            "entryId": row.entry_id,
                            "date": row.date.isoformat(),
                            "amount": _money(row_amount),
                        },
                        evidence=[
                            Evidence(
                                doc_id=row.doc_id,
                                ledger_entry_id=row.entry_id,
                                label="Ledger entry",
                            )
                        ],
                    )
                )

    return out
