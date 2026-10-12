"""Printed strings to canonical values (docs/07 §5.4). Pure and shared by every reading source.

A value that does not parse is `None` with a note; nothing is ever guessed.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

AmountStyle = Literal["EN", "EU"]  # 1,250,000.00 or 1.250.000,00
Direction = Literal["DEBIT", "CREDIT", "AMBIGUOUS"]
PaymentMethod = Literal["CASH", "CARD", "TRANSFER", "UNKNOWN"]

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Parsed[T]:
    value: T | None
    note: str | None = None


# ---------------------------------------------------------------------------- amounts

_CURRENCY = re.compile(r"(?i)\b(?:IDR|MYR|SGD|JPY|USD|RM|RP|S\$|US\$)|[¥$€£]")
_EN = re.compile(r"^\d{1,3}(,\d{3})*(\.\d+)?$|^\d+(\.\d+)?$")
_EU = re.compile(r"^\d{1,3}(\.\d{3})*(,\d+)?$|^\d+(,\d+)?$")


def detect_amount_style(samples: list[str]) -> AmountStyle:
    """The document's format from the majority of its amounts: a comma before the last two digits
    (`1.250.000,00`, `12,50`) votes EU; a dot there votes EN."""
    eu = en = 0
    for text in samples:
        core = re.sub(r"[^\d.,]", "", text or "")
        if re.search(r",\d{2}$", core):
            eu += 1
        elif re.search(r"\.\d{2}$", core):
            en += 1
    return "EU" if eu > en else "EN"


def parse_amount(text: str | None, style: AmountStyle = "EN") -> Parsed[Decimal]:
    if text is None or not text.strip():
        return Parsed(None)
    s = _CURRENCY.sub("", text).strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative, s = True, s[1:-1].strip()
    upper = s.upper()
    if upper.endswith("DR"):
        negative, s = True, s[:-2].strip()
    elif upper.endswith("CR"):
        s = s[:-2].strip()
    if s.endswith("-"):
        negative, s = True, s[:-1].strip()
    if s.startswith("-"):
        negative, s = True, s[1:].strip()
    s = s.replace(" ", "")
    pattern = _EN if style == "EN" else _EU
    if not pattern.match(s):
        return Parsed(None, f"not an amount: {text!r}")
    plain = s.replace(",", "") if style == "EN" else s.replace(".", "").replace(",", ".")
    try:
        value = Decimal(plain).quantize(CENT)
    except InvalidOperation:
        return Parsed(None, f"not an amount: {text!r}")
    return Parsed(-value if negative else value)


# ---------------------------------------------------------------------------- dates

_MONTHS = {
    name: i
    for i, names in enumerate(
        [
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ],
        start=1,
    )
    for name in names
}


def _year(text: str) -> int:
    y = int(text)
    return y + 2000 if y < 100 else y


def _parts(text: str) -> tuple[int, int, int | None] | None:
    """(day, month, year or None) from the formats statements print."""
    s = re.sub(r"\s+", " ", text.strip().lower().replace(",", " "))
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s):
        return int(m[3]), int(m[2]), int(m[1])
    if m := re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})(?:[/.\-](\d{2,4}))?", s):
        return int(m[1]), int(m[2]), _year(m[3]) if m[3] else None
    if m := re.fullmatch(r"(\d{1,2}) ?[ \-]?([a-z]{3,9})\.?(?:[ \-]?(\d{2,4}))?", s):
        month = _MONTHS.get(m[2])
        return (int(m[1]), month, _year(m[3]) if m[3] else None) if month else None
    if m := re.fullmatch(r"([a-z]{3,9}) (\d{1,2})(?: (\d{4}))?", s):
        month = _MONTHS.get(m[1])
        return (int(m[2]), month, int(m[3]) if m[3] else None) if month else None
    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date(text: str | None, *, period: tuple[date, date] | None = None) -> Parsed[date]:
    """Day first, as statements in our markets print. A missing year comes from the statement
    period (which may cross a year end); a date outside the period keeps a note."""
    if not text or not text.strip():
        return Parsed(None)
    parts = _parts(text)
    if parts is None:
        return Parsed(None, f"not a date: {text!r}")
    day, month, year = parts
    if year is None:
        if period is None:
            return Parsed(None, f"no year for {text!r}")
        candidates = [
            d for y in {period[0].year, period[1].year} if (d := _safe_date(y, month, day))
        ]
        inside = [d for d in candidates if period[0] <= d <= period[1]]
        if inside:
            return Parsed(inside[0])
        if not candidates:
            return Parsed(None, f"not a date: {text!r}")
        nearest = min(
            candidates, key=lambda d: min(abs((d - period[0]).days), abs((d - period[1]).days))
        )
        return Parsed(nearest, "outside the statement period")
    value = _safe_date(year, month, day)
    if value is None:
        return Parsed(None, f"not a date: {text!r}")
    if period and not period[0] <= value <= period[1]:
        return Parsed(value, "outside the statement period")
    return Parsed(value)


def parse_period(start_text: str | None, end_text: str | None) -> tuple[date, date] | None:
    """A printed statement period; both ends carry a year on every statement we have seen."""
    start = parse_date(start_text).value
    end = parse_date(end_text).value
    return (start, end) if start and end and start <= end else None


# ---------------------------------------------------------------------------- rows


def direction(debit: Decimal | None, credit: Decimal | None) -> Direction:
    if debit is not None and credit is None:
        return "DEBIT"
    if credit is not None and debit is None:
        return "CREDIT"
    return "AMBIGUOUS"


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", folded).strip().upper()


# The first line names the channel; the party follows on it or on a later line.
_PREFIXES = [
    "INSTANT TRANSFER IN",
    "INSTANT TRANSFER OUT",
    "INTERBANK TRANSFER",
    "TRANSFER IN",
    "TRANSFER OUT",
    "PAYMENT FROM",
    "PAYMENT TO",
    "RTGS",
    "MBK INSTANT TRF DR",
    "MBK INSTANT TRF CR",
    "INSTANT TRF DR",
    "INSTANT TRF CR",
    "DUITNOW QR POS DR",
    "DUITNOW QR POS CR",
    "DUITNOW TRF DR",
    "DUITNOW TRF CR",
    "DEBIT CARD TXN - DR",
    "DEBIT CARD TXN-DR",
    "DEBIT CARD TXN",
    "IBG CREDIT",
    "IBG DEBIT",
]
_NOISE = re.compile(r"^(?:MY|ID|SG|IE|US|AN|QR POS PAYMENT|[A-Z]{2,5}QR\d+|\d+)$")


def _strip_trailing_codes(text: str) -> str:
    """Drop invoice numbers, account digits and trailing dashes after a name."""
    words = text.split()
    while words and (re.search(r"\d", words[-1]) or words[-1] in {"-", "DR", "CR"}):
        words.pop()
    return " ".join(words).rstrip("- ").strip()


def extract_counterparty(description: str | None) -> str | None:
    """A party name after the common prefixes (docs/07 §5.4); the categorizer refines the rest."""
    if not description:
        return None
    lines = [_fold(line) for line in description.splitlines() if line.strip()]
    if not lines:
        return None
    first = lines[0]
    prefix = next((p for p in _PREFIXES if first.startswith(p)), None)
    if prefix is None:
        return None
    rest = _strip_trailing_codes(first[len(prefix) :].strip())
    if rest:
        return rest
    for line in lines[1:]:
        candidate = _strip_trailing_codes(re.sub(r"^\d+\s+", "", line))
        if candidate and not _NOISE.match(candidate) and re.search(r"[A-Z]{2}", candidate):
            return candidate
    return None


def payment_method(text: str | None) -> PaymentMethod:
    if not text:
        return "UNKNOWN"
    t = _fold(text)
    if "CASH" in t or "TUNAI" in t:
        return "CASH"
    if any(k in t for k in ("CARD", "VISA", "MASTERCARD", "AMEX", "DEBIT", "CREDIT")):
        return "CARD"
    if any(k in t for k in ("QR", "TRANSFER", "TRF", "DUITNOW", "QRIS", "FPX")):
        return "TRANSFER"
    return "UNKNOWN"
