"""A dashboard period and the previous one of equal length (spec 010, AC-010-1; contracts Period).

A month (2026-03), quarter (2026-Q1), year (2026), range of at most 12 months (2026-01..2026-06),
recent (the last three months with data) or all (every month with data, no previous period). The
dashboard offers a month (the current one by default), a range or a year. Pure.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

_MONTH = r"\d{4}-(0[1-9]|1[0-2])"
RECENT_MONTHS = 3
MAX_RANGE_MONTHS = 12  # a range longer than a year is not a dashboard period


@dataclass(frozen=True)
class Period:
    key: str
    months: tuple[str, ...]
    previous: tuple[str, ...]  # empty when there is no previous period of equal length


def _index(month: str) -> int:
    year, number = month.split("-")
    return int(year) * 12 + int(number) - 1


def _month(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _span(first: int, last: int) -> tuple[str, ...]:
    return tuple(_month(i) for i in range(first, last + 1))


def _with_previous(key: str, first: int, last: int) -> Period:
    length = last - first + 1
    return Period(key, _span(first, last), _span(first - length, first - 1))


def normalize_period_key(period: str) -> str:
    cleaned = period.strip()
    if cleaned in ("all", "recent"):
        return cleaned
    if m := re.search(
        r"^(?:range[:\s]*)?\(?(\d{4}-(?:0[1-9]|1[0-2])\s*\.\.\s*\d{4}-(?:0[1-9]|1[0-2]))\)?$",
        cleaned,
        re.IGNORECASE,
    ):
        return re.sub(r"\s*", "", m.group(1))
    if m := re.search(r"^(?:quarter[:\s]*)?\(?(\d{4}-Q[1-4])\)?$", cleaned, re.IGNORECASE):
        return m.group(1).upper()
    if m := re.search(r"^(?:month[:\s]*)?\(?(\d{4}-(?:0[1-9]|1[0-2]))\)?$", cleaned, re.IGNORECASE):
        return m.group(1)
    if m := re.search(r"^(?:year[:\s]*)?\(?(\d{4})\)?$", cleaned, re.IGNORECASE):
        return m.group(1)
    return cleaned


def resolve_period(period: str, with_data: Sequence[str]) -> Period:
    """`with_data`: the months that have data, in any order. Raises ValueError for anything else."""
    period = normalize_period_key(period)
    data = sorted(set(with_data))
    if period == "all":
        return Period(period, tuple(data), ())
    if period == "recent":
        if not data:
            return Period(period, (), ())
        last = _index(data[-1])
        first = max(_index(data[0]), last - RECENT_MONTHS + 1)
        return _with_previous(period, first, last)
    if re.fullmatch(_MONTH, period):
        return _with_previous(period, _index(period), _index(period))
    if m := re.fullmatch(r"(\d{4})-Q([1-4])", period):
        first = int(m.group(1)) * 12 + (int(m.group(2)) - 1) * 3
        return _with_previous(period, first, first + 2)
    if re.fullmatch(r"\d{4}", period):
        first = int(period) * 12
        return _with_previous(period, first, first + 11)
    if m := re.fullmatch(rf"({_MONTH})\.\.({_MONTH})", period):
        first, last = _index(m.group(1)), _index(m.group(3))
        if first <= last and last - first < MAX_RANGE_MONTHS:
            return _with_previous(period, first, last)
    raise ValueError(f"Not a period: {period!r}")
