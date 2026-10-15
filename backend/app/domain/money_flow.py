"""Where the money went (docs/08 §5.1; spec 010, T010-01). Pure: bank lines in, nodes and links out.

STATEMENT: sources → accounts → activity under the framework → statement line in its wording.
COUNTERPARTIES: sources → accounts → who was paid. Each account balances by construction
(Σ in = Σ out + kept, with "Taken from balance" when it paid out more than came in). The framework
only moves categories whose cash-flow class differs between frameworks (interest); totals never
change. Wording, groups and splits come from categories.v1.yaml; IDs do not depend on line order.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.core.ids import content_id
from app.domain.categorize import Category, CategoryPolicy, Framework
from app.domain.models.bank_line import BankLine

View = Literal["STATEMENT", "COUNTERPARTIES"]
Column = Literal["SOURCE", "ACCOUNT", "ACTIVITY", "LINE", "USE"]

ZERO = Decimal("0")
TOP_CLIENTS = 5
_ORDER: dict[str, int] = {"SOURCE": 0, "ACCOUNT": 1, "ACTIVITY": 2, "LINE": 3, "USE": 3}


@dataclass(frozen=True)
class FlowNode:
    id: str
    column: Column
    label: str
    value: Decimal
    cashflow_class: str | None = None
    statement_line: str | None = None


@dataclass(frozen=True)
class FlowLink:
    id: str  # "<source>><target>", usable as flow= on /api/bank-lines
    source: str
    target: str
    value: Decimal
    tx_ids: tuple[str, ...] = ()

    @property
    def line_count(self) -> int:
        return len(self.tx_ids)


@dataclass(frozen=True)
class MoneyFlow:
    view: View
    framework: Framework
    nodes: tuple[FlowNode, ...]
    links: tuple[FlowLink, ...]
    excluded_held: Decimal
    note: str | None

    @property
    def total(self) -> Decimal:
        """Money in during the period (every source but the balance)."""
        return sum(
            (n.value for n in self.nodes if n.column == "SOURCE" and n.id != "src:balance"), ZERO
        )

    def lines_of(self, link_id: str) -> tuple[str, ...]:
        return next((link.tx_ids for link in self.links if link.id == link_id), ())


@dataclass(frozen=True)
class _Meta:
    column: Column
    label: str
    cashflow_class: str | None = None
    statement_line: str | None = None


def _client_key(name: str) -> str:
    return " ".join(name.split()).casefold()


class _Builder:
    def __init__(self, policy: CategoryPolicy, framework: Framework) -> None:
        self.policy = policy
        self.framework: Framework = framework
        self.meta: dict[str, _Meta] = {}
        self.amounts: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
        self.txs: dict[tuple[str, str], list[str]] = defaultdict(list)

    def label(self, key: str) -> str:
        return self.policy.flow_labels.get(key, key)

    def node(self, node_id: str, meta: _Meta) -> str:
        self.meta.setdefault(node_id, meta)
        return node_id

    def flow(self, source: str, target: str, value: Decimal, tx_id: str | None = None) -> None:
        self.amounts[(source, target)] += value
        if tx_id is not None:
            self.txs[(source, target)].append(tx_id)

    def result(self, view: View, held: Decimal, note: str | None) -> MoneyFlow:
        into: dict[str, Decimal] = defaultdict(lambda: ZERO)
        out: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for (source, target), value in self.amounts.items():
            out[source] += value
            into[target] += value
        nodes = sorted(
            (
                FlowNode(
                    node_id,
                    m.column,
                    m.label,
                    max(into[node_id], out[node_id]),
                    m.cashflow_class,
                    m.statement_line,
                )
                for node_id, m in self.meta.items()
            ),
            key=lambda n: (_ORDER[n.column], -n.value, n.id),
        )
        links = sorted(
            (
                FlowLink(f"{s}>{t}", s, t, value, tuple(sorted(self.txs.get((s, t), []))))
                for (s, t), value in self.amounts.items()
                if value > 0
            ),
            key=lambda link: (_ORDER[self.meta[link.source].column], -link.value, link.id),
        )
        return MoneyFlow(view, self.framework, tuple(nodes), tuple(links), held, note)


def build_money_flow(
    lines: list[BankLine],
    *,
    account_of: dict[str, str],
    policy: CategoryPolicy,
    framework: Framework,
    view: View = "STATEMENT",
    show_transfers: bool = False,
    held_docs: frozenset[str] = frozenset(),
) -> MoneyFlow:
    """`account_of` maps a statement's docId to its account label (bank and masked number)."""
    b = _Builder(policy, framework)
    unknown = policy.categories["UNKNOWN"]

    def category(line: BankLine) -> Category:
        return policy.categories.get(line.category, unknown)

    held = sum((abs(ln.amount) for ln in lines if ln.doc_id in held_docs), ZERO)
    counted = [ln for ln in lines if ln.doc_id not in held_docs]

    def is_cash_sale(line: BankLine) -> bool:
        return "CASH_DEPOSIT" in line.risk_tags or not (line.counterparty_name or "").strip()

    revenue = [
        ln
        for ln in counted
        if ln.amount > 0 and category(ln).line == "REVENUE" and not is_cash_sale(ln)
    ]
    by_client: dict[str, Decimal] = defaultdict(lambda: ZERO)
    spellings: dict[str, set[str]] = defaultdict(set)
    for ln in revenue:
        key = _client_key(ln.counterparty_name or "")
        by_client[key] += ln.amount
        spellings[key].add(" ".join((ln.counterparty_name or "").split()))
    top = {k for k, _ in sorted(by_client.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_CLIENTS]}

    def account(line: BankLine) -> str:
        name = account_of.get(line.doc_id) or b.label("bankAccount")
        return b.node(f"acc:{content_id('acc', name)}", _Meta("ACCOUNT", name))

    def source(line: BankLine, cat: Category) -> str:
        if cat.line == "REVENUE":
            if is_cash_sale(line):
                return b.node("src:cash", _Meta("SOURCE", b.label("cashSales"), None, "REVENUE"))
            key = _client_key(line.counterparty_name or "")
            if key in top:
                name = sorted(spellings[key])[0]
                return b.node(
                    f"src:client:{content_id('cp', key)}", _Meta("SOURCE", name, None, "REVENUE")
                )
            return b.node(
                "src:other-clients", _Meta("SOURCE", b.label("otherClients"), None, "REVENUE")
            )
        if cat.cashflow_class(framework) == "UNCLASSIFIED":
            return b.node("src:uncategorized", _Meta("SOURCE", b.label("uncategorized")))
        wording = policy.lines[cat.line].label(framework)
        return b.node(f"src:line:{cat.line}", _Meta("SOURCE", wording, None, cat.line))

    def activity_and_line(cat: Category) -> tuple[str, str]:
        cls = cat.cashflow_class(framework)
        activity = b.node(
            f"act:{cls}",
            _Meta("ACTIVITY", b.label("uncategorized" if cls == "UNCLASSIFIED" else cls), cls),
        )
        line_def = policy.lines[cat.line]
        if line_def.split or cls == "UNCLASSIFIED":
            node_id, wording = f"line:{cat.line}:{cat.id}", cat.label
        else:
            node_id, wording = f"line:{cat.line}", line_def.label(framework)
        return activity, b.node(node_id, _Meta("LINE", wording, cls, cat.line))

    def use(cat: Category) -> str:
        group = cat.use or "OTHER"
        return b.node(f"use:{group}", _Meta("USE", policy.uses.get(group, group)))

    for ln in counted:
        cat = category(ln)
        acc = account(ln)
        value = abs(ln.amount)
        if cat.cashflow_class(framework) == "NON_CASH":
            if not show_transfers:
                continue
            if ln.amount > 0:
                own = b.node("src:own-accounts", _Meta("SOURCE", b.label("fromOwnAccounts")))
                b.flow(own, acc, value, ln.tx_id)
            else:
                column: Column = "ACTIVITY" if view == "STATEMENT" else "USE"
                prefix = "act" if view == "STATEMENT" else "use"
                own = b.node(f"{prefix}:own-accounts", _Meta(column, b.label("toOwnAccounts")))
                b.flow(acc, own, value, ln.tx_id)
            continue
        if ln.amount > 0:
            b.flow(source(ln, cat), acc, value, ln.tx_id)
        elif view == "STATEMENT":
            activity, line_node = activity_and_line(cat)
            b.flow(acc, activity, value, ln.tx_id)
            b.flow(activity, line_node, value, ln.tx_id)
        else:
            b.flow(acc, use(cat), value, ln.tx_id)

    # Each account balances: what it kept goes on, what it paid beyond its money in comes from its
    # balance.
    accounts = [node_id for node_id, m in b.meta.items() if m.column == "ACCOUNT"]
    for acc in accounts:
        came_in = sum((v for (s, t), v in b.amounts.items() if t == acc), ZERO)
        went_out = sum((v for (s, t), v in b.amounts.items() if s == acc), ZERO)
        if came_in > went_out:
            kept = (
                b.node("act:KEPT", _Meta("ACTIVITY", b.label("kept")))
                if view == "STATEMENT"
                else b.node("use:KEPT", _Meta("USE", b.label("keptInAccount")))
            )
            b.flow(acc, kept, came_in - went_out)
        elif went_out > came_in:
            balance = b.node("src:balance", _Meta("SOURCE", b.label("takenFromBalance")))
            b.flow(balance, acc, went_out - came_in)

    moved = any(category(ln).ifrs != category(ln).us_gaap for ln in counted)
    note = policy.framework_notes.get(framework) if moved else None
    return b.result(view, held, note)
