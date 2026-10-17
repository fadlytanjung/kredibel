"""How many documents a month the books hold (spec 024). Zero keeps the books as docs/18 describes
them (four sales invoices, the supplier schedule, four receipts a month); a target such as 100 adds
generic sales invoices, supplier invoices and receipts beside them, paid and booked like the rest,
so the demo reads like a real business's month."""

from __future__ import annotations

BASE_PER_MONTH = 13  # four sales invoices, about four supplier invoices, four receipts, a statement
_extra = (0, 0, 0)


def set_volume(per_month: int) -> None:
    """About `per_month` documents a month (0: the books as they are)."""
    global _extra
    more = max(0, per_month - BASE_PER_MONTH)
    sales = round(more * 0.40)
    purchases = round(more * 0.25)
    _extra = (sales, purchases, more - sales - purchases)


def extra() -> tuple[int, int, int]:
    """The extra (sales invoices, supplier invoices, receipts) of each month."""
    return _extra
