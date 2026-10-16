"""Invoices and receipts against the page's words (docs/07 §6.2): header values anywhere on the
page, items anchored on their description with the amount in the item's band."""

from app.domain.verify import Word, check_items, check_value, locate


def _line(top: float, *cells: tuple[str, float]) -> list[Word]:
    out = []
    for text, x in cells:
        width = 0.008 * len(text)
        out.append(Word(text, x, x + width, top, top + 0.012))
    return out


PAGE = [
    *_line(0.05, ("INVOICE", 0.06)),
    *_line(0.08, ("ACMESDN", 0.06), ("BHD", 0.13)),
    *_line(0.11, ("Invoice", 0.60), ("No:", 0.67), ("INV-2026-0042", 0.72)),
    *_line(0.14, ("Date:", 0.60), ("22/12/2025", 0.72)),
    *_line(
        0.20, ("Bill", 0.06), ("to:", 0.10), ("Kopi", 0.14), ("Kita", 0.18), ("Enterprise", 0.22)
    ),
    *_line(0.30, ("Description", 0.06), ("Qty", 0.50), ("Amount", 0.80)),
    *_line(0.33, ("Website", 0.06), ("design", 0.14), ("1", 0.50), ("1,200.00", 0.80)),
    *_line(
        0.36, ("Hosting", 0.06), ("(12", 0.14), ("months)", 0.18), ("1", 0.50), ("300.00", 0.80)
    ),
    *_line(0.39, ("Hosting", 0.06), ("setup", 0.14), ("1", 0.50), ("300.00", 0.80)),
    *_line(0.45, ("Subtotal", 0.60), ("1,800.00", 0.80)),
    *_line(0.48, ("SST", 0.60), ("6%", 0.64), ("108.00", 0.80)),
    *_line(0.51, ("Total", 0.60), ("RM", 0.72), ("1,908.00", 0.80)),
]


def test_a_name_is_found_even_when_the_text_layer_drops_a_space():
    hit = locate("ACME SDN BHD", PAGE)
    assert hit is not None and [w.text for w in hit] == ["ACMESDN", "BHD"]


def test_a_phrase_must_cover_whole_words():
    assert locate("CME SDN", PAGE) is None


def test_header_values_are_agreed_with_their_box_or_single_source():
    number = check_value("INV-2026-0042", "text", PAGE)
    assert number is not None and number.status == "AGREED" and number.bbox is not None
    total = check_value("1,908.00", "amount", PAGE)
    assert total is not None and (total.status, total.witness) == ("AGREED", "1,908.00")
    missing = check_value("9,999.00", "amount", PAGE)
    assert missing is not None and missing.status == "SINGLE_SOURCE"
    assert check_value(None, "amount", PAGE) is None


def test_a_date_printed_with_other_separators_is_found_by_its_digits():
    date = check_value("22-12-2025", "date", PAGE)
    assert date is not None and (date.status, date.witness) == ("AGREED", "22/12/2025")


def test_items_take_the_amount_in_their_own_band_even_when_amounts_repeat():
    items = check_items(
        [
            ("Website design", "1,200.00"),
            ("Hosting (12 months)", "300.00"),
            ("Hosting setup", "300.00"),
        ],
        PAGE,
    )
    assert [i.description.status for i in items] == ["AGREED"] * 3
    assert [i.amount.status for i in items if i.amount] == ["AGREED"] * 3
    tops = [i.amount.bbox.y0 for i in items if i.amount and i.amount.bbox]
    assert tops == sorted(tops) and len(set(tops)) == 3


def test_an_item_not_on_the_page_is_single_source():
    [item] = check_items([("Domain renewal", "50.00")], PAGE)
    assert item.description.status == "SINGLE_SOURCE"
    assert item.amount is not None and item.amount.status == "SINGLE_SOURCE"


def test_amounts_without_separators_and_bare_integers_are_found():
    page = [
        *_line(0.10, ("Consulting", 0.06), ("1200.00", 0.80)),
        *_line(0.13, ("Parking", 0.06), ("15000", 0.80)),
        *_line(0.16, ("Water", 0.06), ("1", 0.80)),
    ]
    items = check_items([("Consulting", "1200.00"), ("Parking", "15000"), ("Water", "1")], page)
    assert [i.amount.status for i in items if i.amount] == ["AGREED"] * 3
    total = check_value("Rp. 15.000", "amount", [*_line(0.2, ("Rp.", 0.6), ("15.000", 0.7))])
    assert total is not None and total.status == "AGREED"


def test_a_tall_stray_ocr_token_does_not_merge_the_lines_around_it():
    # OCR of a photo can return one tall noise token beside the header; the item lines below it
    # stay separate lines, so the description is still found in order (spec 022 phase B).
    stray = Word("FOES", 0.10, 0.16, 0.3438, 0.5603)
    item = [
        Word("Pastry", 0.08, 0.20, 0.3912, 0.4213),
        Word("box", 0.21, 0.27, 0.3922, 0.4213),
        Word("for", 0.28, 0.33, 0.3933, 0.4213),
        Word("tasting", 0.34, 0.46, 0.3933, 0.4235),
    ]
    qty = [
        Word("3", 0.08, 0.10, 0.431, 0.458),
        Word("x", 0.11, 0.13, 0.431, 0.458),
        Word("85,000.00", 0.14, 0.30, 0.431, 0.458),
    ]
    amount = Word("255,000.00", 0.67, 0.86, 0.4375, 0.4644)
    words = [stray, *item, *qty, amount]

    [check] = check_items([("Pastry box for tasting\n3 x 85,000.00", "255,000.00")], words)

    assert check.description.status == "AGREED"
    assert check.amount is not None and check.amount.status == "AGREED"
