"""Categories for bank lines (docs/08 §4.1). Pure: the vocabulary, the keyword rules, the cash-flow
class by accounting framework. Precedence is decided here; the model only fills what rules leave."""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from app.domain.models.bank_line import BankLine

Framework = Literal["IFRS", "US_GAAP"]
CategorizedBy = Literal["USER", "MATCH", "TRANSFER", "RULE", "MODEL", "NONE"]


@dataclass(frozen=True)
class Category:
    id: str
    direction: Literal["in", "out", "either"]
    line: str
    label: str
    ifrs: str
    us_gaap: str
    use: str | None = None  # who was paid, for the money flow's counterparty view
    role: str | None = None  # the counterparty role its lines imply (docs/08 §4.2)
    bucket: str | None = None  # the named bucket for its unnamed lines ("Bank fees")
    pnl_line: str | None = None  # cash-basis profit and loss (ADR-027 amendment): the P&L line
    subledger: str | None = None  # and the subledger label; None for transfers, reversals, UNKNOWN

    def cashflow_class(self, framework: Framework) -> str:
        return self.ifrs if framework == "IFRS" else self.us_gaap


@dataclass(frozen=True)
class StatementLine:
    """A cash-basis statement line, worded per framework; `split` lines show one chart node per
    category (docs/08 §5.1)."""

    id: str
    order: int
    ifrs: str
    us_gaap: str
    split: bool = False

    def label(self, framework: Framework) -> str:
        return self.ifrs if framework == "IFRS" else self.us_gaap


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    direction: Literal["in", "out", "either"]
    category: str | None  # None: tags only, the category is left to the model
    risk_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryPolicy:
    categories: dict[str, Category]
    rules: tuple[Rule, ...]
    min_model_confidence: Decimal = Decimal("0.5")
    lines: dict[str, StatementLine] = field(default_factory=dict)
    uses: dict[str, str] = field(default_factory=dict)
    flow_labels: dict[str, str] = field(default_factory=dict)
    framework_notes: dict[str, str] = field(default_factory=dict)

    def allowed(self, amount: Decimal) -> list[str]:
        """What the model may choose for a line of this direction."""
        way = "in" if amount > 0 else "out"
        return [c.id for c in self.categories.values() if c.direction in (way, "either")]


def parse_category_policy(categories: dict[str, Any], rules: dict[str, Any]) -> CategoryPolicy:
    cats = {
        c["id"]: Category(
            c["id"],
            c["direction"],
            c["line"],
            c["label"],
            c["ifrs"],
            c["usGaap"],
            c.get("use"),
            c.get("counterpartyRole"),
            c.get("bucket"),
            c.get("pnlLine"),
            c.get("subledger"),
        )
        for c in categories["categories"]
    }
    lines = {
        line_id: StatementLine(
            line_id, int(v["order"]), v["ifrs"], v["usGaap"], bool(v.get("split", False))
        )
        for line_id, v in (categories.get("lines") or {}).items()
    }
    parsed = tuple(
        Rule(
            id=r["id"],
            pattern=re.compile(r["pattern"], re.IGNORECASE),
            direction=r.get("direction", "either"),
            category=r.get("category"),
            risk_tags=tuple(r.get("riskTags") or ()),
        )
        for r in rules["rules"]
    )
    for r in parsed:
        if r.category is not None and r.category not in cats:
            raise ValueError(f"rule {r.id} names unknown category {r.category}")
    for c in cats.values():
        if lines and c.line not in lines:
            raise ValueError(f"category {c.id} names unknown statement line {c.line}")
    return CategoryPolicy(
        cats,
        parsed,
        lines=lines,
        uses=dict(categories.get("uses") or {}),
        flow_labels=dict(categories.get("flowLabels") or {}),
        framework_notes=dict(categories.get("frameworkNotes") or {}),
    )


@dataclass
class Categorized:
    category: str
    categorized_by: CategorizedBy
    confidence: Decimal | None = None
    risk_tags: list[str] = field(default_factory=list)
    rule_id: str | None = None


def _text(description: str, counterparty: str | None) -> str:
    return " ".join(f"{description} {counterparty or ''}".upper().split())


def by_rules(
    description: str, counterparty: str | None, amount: Decimal, policy: CategoryPolicy
) -> tuple[Categorized | None, list[str]]:
    """The first rule that matches the line's direction decides; tag-only rules add risk tags and
    leave the category to the model. Returns (decision or None, risk tags from every match)."""
    text = _text(description, counterparty)
    way = "in" if amount > 0 else "out"
    tags: list[str] = []
    decided: Categorized | None = None
    for rule in policy.rules:
        if rule.direction not in (way, "either") or not rule.pattern.search(text):
            continue
        tags += [t for t in rule.risk_tags if t not in tags]
        if decided is None and rule.category is not None:
            decided = Categorized(rule.category, "RULE", rule_id=rule.id)
    if decided is not None:
        decided.risk_tags = tags
    return decided, tags


def from_model(
    category: str | None,
    confidence: float | None,
    amount: Decimal,
    tags: list[str],
    policy: CategoryPolicy,
) -> Categorized:
    """The model's answer, kept only when it is allowed for the line's direction and confident."""
    sure = confidence is not None and Decimal(str(confidence)) >= policy.min_model_confidence
    if category in policy.allowed(amount) and sure and category != "UNKNOWN":
        return Categorized(category, "MODEL", Decimal(str(confidence)), tags)  # type: ignore[arg-type]
    return Categorized(
        "UNKNOWN", "NONE", None if confidence is None else Decimal(str(confidence)), tags
    )


def keep_person_categories(read: list[BankLine], stored: list[BankLine]) -> list[BankLine]:
    """A statement read again keeps every category a person chose (AC-007-2, non-negotiable 17):
    the line has the same ID, so its category, cash-flow class and who decided it carry over."""
    chosen = {line.tx_id: line for line in stored if line.categorized_by == "USER"}
    for line in read:
        if (person := chosen.get(line.tx_id)) is not None:
            line.category, line.categorized_by = person.category, "USER"
            line.cashflow_class, line.category_confidence = person.cashflow_class, None
    return read


def category_fits(category: Category, amount: Decimal) -> bool:
    """A category is for money in, money out or either; a line takes one of its own direction."""
    return category.direction == "either" or category.direction == ("in" if amount > 0 else "out")
