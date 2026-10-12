"""Normalization of printed values (docs/07 §5.4, T005-01).

Shapes come from synthetic statements and a real Malaysian one (spike S1), with invented values.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.normalize import (
    detect_amount_style,
    direction,
    extract_counterparty,
    parse_amount,
    parse_date,
    parse_period,
    payment_method,
)

D = Decimal


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1,250,000.00", D("1250000.00")),
        ("IDR 1,250,000.00", D("1250000.00")),
        ("RM 2,345.67", D("2345.67")),
        ("Rp1.250.000", None),  # dot-grouped needs the EU style
        ("12.50", D("12.50")),
        ("3,000", D("3000.00")),  # yen without decimals
        ("¥3,000", D("3000.00")),
        ("1,234.56 CR", D("1234.56")),
        ("1,234.56 DR", D("-1234.56")),
        ("1,234.56-", D("-1234.56")),
        ("(1,234.56)", D("-1234.56")),
        ("-45.00", D("-45.00")),
        ("S$ 980.05", D("980.05")),
    ],
)
def test_amounts_in_english_format(text, value):
    assert parse_amount(text).value == value


def test_dot_grouped_amounts_once_the_document_style_is_known():
    style = detect_amount_style(["1.250.000,00", "32.100.000,00", "12,50"])
    assert style == "EU"
    assert parse_amount("Rp1.250.000,00", style).value == D("1250000.00")
    assert parse_amount("12,50", style).value == D("12.50")


def test_the_majority_decides_the_style():
    assert detect_amount_style(["1,250.00", "9,999.99", "45.00"]) == "EN"
    assert detect_amount_style([]) == "EN"


@pytest.mark.parametrize("text", ["", None, "n/a", "1,2,3.4.5", "12abc"])
def test_what_does_not_parse_is_none_with_a_note(text):
    parsed = parse_amount(text)
    assert parsed.value is None
    assert parsed.note or text in ("", None)


def test_a_statement_period_as_printed():
    assert parse_period("16 Aug 26", "15 Sep 26") == (date(2026, 8, 16), date(2026, 9, 15))
    assert parse_period("01/03/2026", "31/03/2026") == (date(2026, 3, 1), date(2026, 3, 31))
    assert parse_period("1 March 2026", "31 March 2026") == (date(2026, 3, 1), date(2026, 3, 31))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("16Aug", date(2026, 8, 16)),
        ("16 Aug", date(2026, 8, 16)),
        ("05 Sep", date(2026, 9, 5)),
        ("16/08", date(2026, 8, 16)),
        ("16/08/2026", date(2026, 8, 16)),
        ("16-08-26", date(2026, 8, 16)),
        ("16-Aug-26", date(2026, 8, 16)),
        ("2026-08-16", date(2026, 8, 16)),
        ("16.08.2026", date(2026, 8, 16)),
    ],
)
def test_dates_take_their_year_from_the_period(text, expected):
    period = (date(2026, 8, 16), date(2026, 9, 15))
    assert parse_date(text, period=period).value == expected


def test_a_period_across_new_year():
    period = (date(2025, 12, 16), date(2026, 1, 15))
    assert parse_date("20 Dec", period=period).value == date(2025, 12, 20)
    assert parse_date("03 Jan", period=period).value == date(2026, 1, 3)


def test_a_date_outside_the_period_keeps_a_note():
    parsed = parse_date("02 Jul", period=(date(2026, 8, 16), date(2026, 9, 15)))
    assert parsed.value == date(2026, 7, 2)
    assert parsed.note == "outside the statement period"


def test_direction():
    assert direction(D("10"), None) == "DEBIT"
    assert direction(None, D("10")) == "CREDIT"
    assert direction(D("10"), D("10")) == "AMBIGUOUS"
    assert direction(None, None) == "AMBIGUOUS"


@pytest.mark.parametrize(
    ("description", "party"),
    [
        ("TRANSFER IN HARBORVIEW HOTEL GROUP INV/SCR/2026/03/0009", "HARBORVIEW HOTEL GROUP"),
        ("INSTANT TRANSFER IN DAYBREAK CAFE", "DAYBREAK CAFE"),
        ("TRANSFER OUT GREEN VALLEY FARMS 7312", "GREEN VALLEY FARMS"),
        ("DEBIT CARD TXN - DR\n123456 GRAB RIDES-\nMY", "GRAB RIDES"),
        (
            "DUITNOW QR POS DR\nMBBQR1234567\nQR POS Payment\nD cempaka An cubic\nMBBQR1234567",
            "D CEMPAKA AN CUBIC",
        ),
        ("MBK INSTANT TRF DR\nNURUL AINA BINTI AHMAD\nRent Sept", "NURUL AINA BINTI AHMAD"),
        ("ADMIN FEE", None),
        ("CASH DEPOSIT", None),
    ],
)
def test_counterparty_after_common_prefixes(description, party):
    assert extract_counterparty(description) == party


@pytest.mark.parametrize(
    ("text", "method"),
    [
        ("CASH", "CASH"),
        ("DEBIT CARD ••4821", "CARD"),
        ("VISA ****1234", "CARD"),
        ("QRIS", "TRANSFER"),
        ("DuitNow QR", "TRANSFER"),
        ("Bank transfer", "TRANSFER"),
        (None, "UNKNOWN"),
        ("voucher", "UNKNOWN"),
    ],
)
def test_receipt_payment_method(text, method):
    assert payment_method(text) == method


# Found on real Malaysian and Indonesian invoices and receipts (spec 005, T005-03).


def test_a_currency_with_a_dot_is_stripped():
    assert parse_amount("Rp. 15.000", "EU").value == Decimal("15000.00")
    assert parse_amount("RM 1,200.00").value == Decimal("1200.00")


def test_whole_amounts_grouped_by_dots_are_detected_as_dot_grouped():
    assert detect_amount_style(["Rp. 15.000", "1.500.000", "Rp 250.000"]) == "EU"
    assert detect_amount_style(["1,500,000", "250,000"]) == "EN"
    assert detect_amount_style(["1,200.00", "300.00"]) == "EN"


def test_malay_and_indonesian_month_names_parse():
    assert parse_date("22 Disember 2025").value == date(2025, 12, 22)
    assert parse_date("5 Ogos 2026").value == date(2026, 8, 5)
    assert parse_date("17 Agustus 2026").value == date(2026, 8, 17)
    assert parse_date("1 Mac 2026").value == date(2026, 3, 1)
    assert parse_date("30 Okt 2026").value == date(2026, 10, 30)
