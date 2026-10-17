"""The demo at a real business's volume (spec 024): about a hundred files a month, the books' own
documents first and generic ones beside them, every one paid and booked like the rest."""

import re
from collections import Counter

from kredibel_synth.books import generate_books
from kredibel_synth.volume import set_volume


def test_ac024_1_a_month_holds_about_a_hundred_documents_all_paid_and_booked():
    set_volume(100)
    try:
        books = generate_books(1)
    finally:
        set_volume(0)
    per_month = Counter(
        re.search(r"(\d{4}-\d{2})", d.key).group(1)  # type: ignore[union-attr]
        for d in (*books.sales, *books.purchases, *books.receipts)
    )
    for month, count in per_month.items():
        assert 90 <= count + 1 <= 110, (month, count)  # plus the statement
    paid = {key for st in books.statements.values() for row in st.rows for key in row.documents}
    unpaid = [inv.key for inv in books.sales if inv.key not in paid]
    assert len(unpaid) <= 3, unpaid  # only the planted not-yet-due and special cases
    keys = [d.key for d in (*books.sales, *books.purchases, *books.receipts)]
    assert len(keys) == len(set(keys))
    numbers = [inv.number for inv in (*books.sales, *books.purchases)]
    assert len(numbers) == len(set(numbers))


def test_without_a_volume_the_books_are_unchanged():
    set_volume(0)
    books = generate_books(1)
    assert len(books.sales) == 24 and len(books.receipts) == 24
