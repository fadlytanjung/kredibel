"""A01, A02, A04: do the printed numbers add up (docs/08 §2.3).

CRITICAL only on agreed values (P6): a break among values the readers did not both confirm is
reading uncertainty (E01), not tampering.
"""

from decimal import Decimal

from app.domain.findings import Evidence, Finding
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocType
from app.domain.models.invoice import Invoice, Receipt

from .base import CheckContext, check

_E01 = "E01_LOW_EXTRACTION_AGREEMENT"


def _agreed(line: BankLine, *fields: str) -> bool:
    return all(line.consensus.get(f, {}).get("status") == "AGREED" for f in fields)


def _evidence(ctx: CheckContext, line: BankLine, field: str, label: str) -> Evidence:
    c = line.consensus.get(field, {})
    return Evidence(
        doc_id=ctx.doc_id,
        page=c.get("page") or line.page,
        bbox=c.get("bbox"),
        tx_id=line.tx_id,
        label=label,
    )


def _money(v: Decimal) -> str:
    return f"{v:.2f}"


def _uncertain(
    ctx: CheckContext,
    anchor: str,
    title: str,
    facts: dict[str, str],
    evidence: list[Evidence],
    month: str | None,
) -> list[Finding]:
    if _E01 not in ctx.policy.enabled:
        return []
    return [
        ctx.finding(
            _E01,
            anchor,
            category="EXTRACTION",
            severity="MEDIUM",
            title=title,
            facts=facts,
            evidence=evidence,
            month=month,
        )
    ]


@check("A01_RUNNING_BALANCE_BREAK")
def running_balance(ctx: CheckContext) -> list[Finding]:
    if ctx.doc.doc_type != DocType.BANK_STATEMENT or not ctx.lines:
        return []
    tol = Decimal(ctx.policy.arithmetic.balance_tolerance_minor) / 100
    lines = sorted(ctx.lines, key=lambda ln: ln.row_index)
    out: list[Finding] = []
    prev = ctx.opening
    prev_line: BankLine | None = None
    witness_between = False
    for i, line in enumerate(lines):
        witness_between |= line.source == "WITNESS"
        if line.balance is None:
            prev = None if prev is None else prev + line.amount
            continue
        if prev is not None and abs(prev + line.amount - line.balance) > tol:
            expected = prev + line.amount
            nxt = next((n for n in lines[i + 1 :] if n.balance is not None), None)
            continues = nxt is not None and abs(line.balance + nxt.amount - nxt.balance) <= tol  # type: ignore[operator]
            facts = {
                "row": str(line.row_index + 1),
                "date": line.date.isoformat(),
                "previousBalance": _money(prev),
                "amount": _money(line.amount),
                "expectedBalance": _money(expected),
                "printedBalance": _money(line.balance),
                "difference": _money(line.balance - expected),
                "continuesFromPrinted": "yes" if continues else "no",
            }
            evidence = [
                _evidence(ctx, line, "balance", "Printed balance"),
                _evidence(ctx, line, "amount", "Amount"),
            ]
            if prev_line is not None:
                evidence.insert(0, _evidence(ctx, prev_line, "balance", "Previous balance"))
            agreed = (
                _agreed(line, "amount", "balance")
                and (prev_line is None or _agreed(prev_line, "balance"))
                and not witness_between
            )
            if agreed:
                out.append(
                    ctx.finding(
                        "A01_RUNNING_BALANCE_BREAK",
                        line.tx_id,
                        category="ARITHMETIC",
                        severity="CRITICAL",
                        month=line.month,
                        facts=facts,
                        evidence=evidence,
                        title=f"The balance on {line.date:%d %b} does not follow from the last",
                    )
                )
            else:
                out += _uncertain(
                    ctx,
                    f"A01|{line.tx_id}",
                    f"The balance on {line.date:%d %b} could not be confirmed",
                    facts,
                    evidence,
                    line.month,
                )
        prev, prev_line, witness_between = line.balance, line, False
    return out


@check("A02_OPENING_CLOSING_MISMATCH")
def opening_closing(ctx: CheckContext) -> list[Finding]:
    if ctx.doc.doc_type != DocType.BANK_STATEMENT or ctx.opening is None or ctx.closing is None:
        return []
    tol = Decimal(ctx.policy.arithmetic.balance_tolerance_minor) / 100
    credits = sum((ln.amount for ln in ctx.lines if ln.amount > 0), Decimal(0))
    debits = -sum((ln.amount for ln in ctx.lines if ln.amount < 0), Decimal(0))
    expected = ctx.opening + credits - debits
    if abs(expected - ctx.closing) <= tol:
        return []
    facts = {
        "opening": _money(ctx.opening),
        "credits": _money(credits),
        "debits": _money(debits),
        "expectedClosing": _money(expected),
        "printedClosing": _money(ctx.closing),
        "difference": _money(ctx.closing - expected),
    }
    last = max(ctx.lines, key=lambda ln: ln.row_index) if ctx.lines else None
    evidence = [_evidence(ctx, last, "balance", "Closing balance")] if last else []
    month = last.month if last else None
    if all(_agreed(ln, "amount") for ln in ctx.lines):
        return [
            ctx.finding(
                "A02_OPENING_CLOSING_MISMATCH",
                "statement",
                category="ARITHMETIC",
                severity="CRITICAL",
                title="Opening balance plus the transactions does not give the closing balance",
                facts=facts,
                evidence=evidence,
                month=month,
            )
        ]
    return _uncertain(
        ctx, "A02", "The closing balance could not be confirmed", facts, evidence, month
    )


def _invoice_problems(
    ctx: CheckContext, inv: Invoice, tol: Decimal
) -> list[tuple[str, dict[str, str], list[Evidence]]]:
    def ev(field: str, label: str) -> Evidence:
        c = inv.consensus.get(field, {})
        return Evidence(
            doc_id=ctx.doc_id,
            page=c.get("page"),
            bbox=c.get("bbox"),
            invoice_id=inv.invoice_id,
            label=label,
        )

    problems: list[tuple[str, dict[str, str], list[Evidence]]] = []
    amounts = [ln.amount for ln in inv.lines if ln.amount is not None]
    complete = bool(amounts) and len(amounts) == len(inv.lines)
    if inv.subtotal is not None and complete:
        lines_sum = sum(amounts, Decimal(0))
        if abs(lines_sum - inv.subtotal) > tol * len(amounts):
            facts = {"linesSum": _money(lines_sum), "printedSubtotal": _money(inv.subtotal)}
            problems.append(("lines", facts, [ev("subtotal", "Subtotal")]))
    if (
        inv.subtotal is not None
        and inv.tax is not None
        and inv.total is not None
        and abs(inv.subtotal + inv.tax - inv.total) > tol
    ):
        facts = {
            "subtotal": _money(inv.subtotal),
            "tax": _money(inv.tax),
            "expectedTotal": _money(inv.subtotal + inv.tax),
            "printedTotal": _money(inv.total),
        }
        problems.append(("total", facts, [ev("total", "Total")]))
    for i, ln in enumerate(inv.lines):
        if (
            ln.quantity is not None
            and ln.unit_price is not None
            and ln.amount is not None
            and abs(ln.quantity * ln.unit_price - ln.amount) > tol
        ):
            facts = {
                "line": str(i + 1),
                "quantity": str(ln.quantity),
                "unitPrice": _money(ln.unit_price),
                "printedAmount": _money(ln.amount),
            }
            problems.append((f"line{i}", facts, [ev(f"lines.{i}.amount", "Line amount")]))
    return problems


def _receipt_problem(ctx: CheckContext, rc: Receipt, tol: Decimal) -> Finding | None:
    amounts = [i.amount for i in rc.items if i.amount is not None]
    if rc.total is None or not amounts or len(amounts) != len(rc.items):
        return None
    items = sum(amounts, Decimal(0))
    tax = rc.tax or Decimal(0)
    allowed = tol * len(amounts)
    # Prices in our markets often include the tax (SST, PPN): either reading may add up.
    if abs(items + tax - rc.total) <= allowed or abs(items - rc.total) <= allowed:
        return None
    c = rc.consensus.get("total", {})
    return ctx.finding(
        "A04_INVOICE_TOTAL_MISMATCH",
        f"{rc.receipt_id}|total",
        category="ARITHMETIC",
        severity="HIGH",
        title="The receipt's items do not add up to its total",
        facts={"itemsSum": _money(items), "tax": _money(tax), "printedTotal": _money(rc.total)},
        evidence=[
            Evidence(
                doc_id=ctx.doc_id,
                page=c.get("page"),
                bbox=c.get("bbox"),
                receipt_id=rc.receipt_id,
                label="Total",
            )
        ],
        month=rc.month,
    )


@check("A04_INVOICE_TOTAL_MISMATCH")
def invoice_totals(ctx: CheckContext) -> list[Finding]:
    tol = Decimal(ctx.policy.arithmetic.invoice_line_tolerance_minor) / 100
    out: list[Finding] = []
    for inv in ctx.invoices:
        for anchor, facts, evidence in _invoice_problems(ctx, inv, tol):
            out.append(
                ctx.finding(
                    "A04_INVOICE_TOTAL_MISMATCH",
                    f"{inv.invoice_id}|{anchor}",
                    category="ARITHMETIC",
                    severity="HIGH",
                    title=f"Invoice {inv.number} does not add up"
                    if inv.number
                    else "The invoice does not add up",
                    facts=facts,
                    evidence=evidence,
                    month=inv.month,
                )
            )
    out += [f for rc in ctx.receipts if (f := _receipt_problem(ctx, rc, tol)) is not None]
    return out
