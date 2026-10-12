"""Categories for bank lines (docs/08 §4.1). Pure: the vocabulary, the keyword rules, the cash-flow
class by accounting framework. Precedence is decided here; the model only fills what rules leave."""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

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

    def cashflow_class(self, framework: Framework) -> str:
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

    def allowed(self, amount: Decimal) -> list[str]:
        """What the model may choose for a line of this direction."""
        way = "in" if amount > 0 else "out"
        return [c.id for c in self.categories.values() if c.direction in (way, "either")]


def parse_category_policy(categories: dict[str, Any], rules: dict[str, Any]) -> CategoryPolicy:
    cats = {
        c["id"]: Category(c["id"], c["direction"], c["line"], c["label"], c["ifrs"], c["usGaap"])
        for c in categories["categories"]
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
    return CategoryPolicy(cats, parsed)


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
