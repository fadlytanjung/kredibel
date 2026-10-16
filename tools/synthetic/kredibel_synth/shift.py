"""Move the books by whole months (docs/18 §5: the demo workspace's books end last month).

The world is written for January to June 2026. `set_shift(n)` moves every date, month key, file
name and printed month of the books by n months after they are built and before they are rendered,
so the scenarios' edits, copies and diversions land on the same rows n months later. With no shift
(the default) every function returns its input and the output is byte for byte the same.
"""

import calendar
import re
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from typing import Any

from . import world

_SHIFT = 0
_ISO = re.compile(r"(?<!\d)(20\d\d)([-/])(0[1-9]|1[0-2])(?!\d)")
_GVF = re.compile(r"\bGVF-(20\d\d)-(0[1-9]|1[0-2])(\d\d)\b")
_PP = re.compile(r"\bPP/(\d\d)/(0[1-9]|1[0-2])(\d\d)\b")
_ABBR = world.MONTH_ABBR
_NAMES = [n.title() for n in world.MONTH_NAME]


def set_shift(months: int) -> None:
    global _SHIFT
    _SHIFT = months


def shift() -> int:
    return _SHIFT


def _ym(year: int, month: int) -> tuple[int, int]:
    index = year * 12 + month - 1 + _SHIFT
    return index // 12, index % 12 + 1


def month(key: str) -> str:
    """ "2026-03" → the shifted month key."""
    if not _SHIFT:
        return key
    year, number = _ym(int(key[:4]), int(key[5:7]))
    return f"{year:04d}-{number:02d}"


def months() -> list[str]:
    return [month(m) for m in world.MONTHS]


def day(d: date) -> date:
    """The same day n months later; a month's last day stays its last day."""
    if not _SHIFT:
        return d
    year, number = _ym(d.year, d.month)
    last = calendar.monthrange(year, number)[1]
    was_last = d.day == calendar.monthrange(d.year, d.month)[1]
    return d.replace(year=year, month=number, day=last if was_last else min(d.day, last))


def moment(dt: datetime) -> datetime:
    if not _SHIFT:
        return dt
    moved = day(dt.date())
    return dt.replace(year=moved.year, month=moved.month, day=moved.day)


def text(value: str) -> str:
    """Month keys and dated identifiers: inv-sales-2026-03-01, statement-2026-03.pdf, 2026/03/."""
    if not _SHIFT:
        return value

    def iso(m: re.Match[str]) -> str:
        year, number = _ym(int(m.group(1)), int(m.group(3)))
        return f"{year:04d}{m.group(2)}{number:02d}"

    def gvf(m: re.Match[str]) -> str:
        year, number = _ym(int(m.group(1)), int(m.group(2)))
        return f"GVF-{year:04d}-{number:02d}{m.group(3)}"

    def pp(m: re.Match[str]) -> str:
        year, number = _ym(2000 + int(m.group(1)), int(m.group(2)))
        return f"PP/{year % 100:02d}/{number:02d}{m.group(3)}"

    return _PP.sub(pp, _GVF.sub(gvf, _ISO.sub(iso, value)))


def words(value: str) -> str:
    """A printed description: dated identifiers, and month names (MAR, March, Mar)."""
    if not _SHIFT:
        return value
    out = text(value)
    for names in (_ABBR, _NAMES, [n[:3] for n in _NAMES]):
        pattern = re.compile(r"\b(" + "|".join(names) + r")\b")
        out = pattern.sub(
            lambda m, names=names: names[(names.index(m.group(1)) + _SHIFT) % 12], out
        )
    return out


def ledger_file() -> str:
    first, last = months()[0], months()[-1]
    return "ledger-2026-H1.csv" if not _SHIFT else f"ledger-{first}_{last}.csv"


def _move(value: Any, name: str = "") -> Any:
    if isinstance(value, datetime):
        return moment(value)
    if isinstance(value, date):
        return day(value)
    if isinstance(value, str):
        return words(value) if name == "description" else text(value)
    if isinstance(value, list):
        return [_move(v, name) for v in value]
    if isinstance(value, tuple):
        return tuple(_move(v, name) for v in value)
    if isinstance(value, dict):
        return {(text(k) if isinstance(k, str) else k): _move(v, name) for k, v in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        moved = {f.name: _move(getattr(value, f.name), f.name) for f in fields(value)}
        if value.__dataclass_params__.frozen:  # type: ignore[attr-defined]
            return replace(value, **moved)
        for key, item in moved.items():
            setattr(value, key, item)
        return value
    return value


def shift_books(books: Any) -> None:
    """Move every date, key and printed month of the books in place (no-op without a shift)."""
    if _SHIFT:
        _move(books)
