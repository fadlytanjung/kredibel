"""What a person expects against what the documents show (spec 024, AC-024-5). Pure.

A person may write the money in and out they expect for a month. Once the month is reconciled, each
direction is as expected (within the tolerance of the expected amount), or different by an amount
the person can follow to the month, its transactions and its documents. The expectation may be
wrong: Kredibel shows the comparison and never judges it.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Status = Literal["AS_EXPECTED", "DIFFERENT", "WAITING"]


@dataclass(frozen=True)
class Expectation:
    month: str  # yyyy-mm
    money_in: Decimal | None = None
    money_out: Decimal | None = None


@dataclass(frozen=True)
class Actual:
    month: str
    money_in: Decimal
    money_out: Decimal  # positive
    reconciled: bool


@dataclass(frozen=True)
class Side:
    expected: Decimal
    actual: Decimal | None
    difference: Decimal | None  # actual minus expected
    status: Status


@dataclass(frozen=True)
class MonthComparison:
    month: str
    money_in: Side | None
    money_out: Side | None


def _side(expected: Decimal | None, actual: Decimal | None, tolerance: Decimal) -> Side | None:
    if expected is None:
        return None
    if actual is None:
        return Side(expected, None, None, "WAITING")
    difference = actual - expected
    within = abs(difference) <= abs(expected) * tolerance
    return Side(expected, actual, difference, "AS_EXPECTED" if within else "DIFFERENT")


def compare_expectations(
    expectations: list[Expectation], actuals: dict[str, Actual], tolerance: Decimal
) -> list[MonthComparison]:
    out: list[MonthComparison] = []
    for e in sorted(expectations, key=lambda e: e.month):
        found = actuals.get(e.month)
        ready = found if found is not None and found.reconciled else None
        out.append(
            MonthComparison(
                e.month,
                _side(e.money_in, ready.money_in if ready else None, tolerance),
                _side(e.money_out, ready.money_out if ready else None, tolerance),
            )
        )
    return out
