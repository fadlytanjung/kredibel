"""Statement verification: the AI reading against the witness words (docs/07 §6.1, T005-02)."""

from app.domain.verify import AiRow, Word, verify_header, verify_statement_page

# Columns as on the synthetic ACB statement and the real RHB one: date, description, debit, credit,
# balance, with amounts right-aligned. Coordinates are normalized to the page (0..1).
DATE_X, DESC_X, DEBIT_X, CREDIT_X, BAL_X = 0.06, 0.16, 0.62, 0.76, 0.90


def _row(
    top: float, date: str, desc: list[str], debit: str | None, credit: str | None, bal: str
) -> list[Word]:
    h = 0.012
    words = [Word(date, DATE_X, DATE_X + 0.06, top, top + h)]
    for i, line in enumerate(desc):
        x = DESC_X
        for part in line.split(" "):
            words.append(Word(part, x, x + 0.01 * len(part), top + i * 0.014, top + i * 0.014 + h))
            x += 0.01 * len(part) + 0.005
    for text, right in ((debit, DEBIT_X), (credit, CREDIT_X), (bal, BAL_X)):
        if text:
            words.append(Word(text, right - 0.008 * len(text), right, top, top + h))
    return words


PAGE = [
    *_row(
        0.30,
        "05/03/2026",
        ["TRANSFER IN HARBORVIEW HOTEL GROUP"],
        None,
        "32,100,000.00",
        "184,048,975.00",
    ),
    *_row(0.34, "06/03/2026", ["DEBIT CARD SWIFT COURIER"], "355,200.00", None, "183,693,775.00"),
    *_row(
        0.38,
        "09/03/2026",
        ["TRANSFER OUT GREEN VALLEY FARMS 7312"],
        "27,250,500.00",
        None,
        "156,443,275.00",
    ),
]
AI = [
    AiRow(
        0,
        "05/03/2026",
        "TRANSFER IN HARBORVIEW HOTEL GROUP",
        None,
        "32,100,000.00",
        "184,048,975.00",
    ),
    AiRow(1, "06/03/2026", "DEBIT CARD SWIFT COURIER", "355,200.00", None, "183,693,775.00"),
    AiRow(
        2,
        "09/03/2026",
        "TRANSFER OUT GREEN VALLEY FARMS 7312",
        "27,250,500.00",
        None,
        "156,443,275.00",
    ),
]


def test_every_value_agrees_with_its_box():
    result = verify_statement_page(AI, PAGE, page=1)
    assert [r.source for r in result.rows] == ["AI", "AI", "AI"]
    for row in result.rows:
        for name in ("date", "description", "balance"):
            assert row.fields[name].status == "AGREED", (row.row_on_page, name)
    credit = result.rows[0].fields["credit"]
    assert credit.status == "AGREED" and credit.bbox is not None
    assert credit.bbox.x1 == CREDIT_X
    assert result.agreement == 1.0


def test_a_text_layer_without_spaces_still_agrees():
    page = [
        *_row(
            0.30, "16Aug", ["DEBITCARDTXN-DR", "123456 GRABRIDES-", "MY"], "12.40", None, "1,204.33"
        ),
        *_row(0.36, "17Aug", ["DUITNOWQRPOSDR", "MBBQR1234567"], "8.50", None, "1,195.83"),
    ]
    ai = [
        AiRow(0, "16 Aug", "DEBIT CARD TXN-DR\n123456 GRAB RIDES-\nMY", "12.40", None, "1,204.33"),
        AiRow(1, "17 Aug", "DUITNOW QR POS DR\nMBBQR1234567", "8.50", None, "1,195.83"),
    ]
    result = verify_statement_page(ai, page, page=2)
    assert all(f.status == "AGREED" for r in result.rows for f in r.fields.values())


def test_a_different_value_in_the_same_cell_is_a_conflict():
    ai = [AI[0]._replace(credit_text="7,250,000.00"), *AI[1:]]
    result = verify_statement_page(ai, PAGE, page=1)
    credit = result.rows[0].fields["credit"]
    assert credit.status == "CONFLICT"
    assert (credit.ai, credit.witness) == ("7,250,000.00", "32,100,000.00")
    assert result.agreement < 1.0


def test_a_value_read_in_the_wrong_column_is_a_conflict():
    ai = [AI[0], AI[1]._replace(debit_text=None, credit_text="355,200.00"), AI[2]]
    result = verify_statement_page(ai, PAGE, page=1)
    assert result.rows[1].fields["credit"].status == "CONFLICT"
    assert result.rows[1].fields["debit"].status == "CONFLICT"


def test_a_value_only_the_ai_reports_is_single_source():
    page = [w for w in PAGE if w.text != "355,200.00"]
    result = verify_statement_page(AI, page, page=1)
    debit = result.rows[1].fields["debit"]
    assert debit.status == "SINGLE_SOURCE" and debit.bbox is not None  # the row band


def test_a_row_only_the_witness_has_is_inserted_in_printed_order():
    page = [*PAGE, *_row(0.42, "10/03/2026", ["ADMIN FEE"], "25,000.00", None, "156,418,275.00")]
    result = verify_statement_page(AI, page, page=1)
    assert [r.source for r in result.rows] == ["AI", "AI", "AI", "WITNESS"]
    extra = result.rows[3]
    assert (
        extra.fields["debit"].witness == "25,000.00"
        and extra.fields["debit"].status == "SINGLE_SOURCE"
    )
    assert extra.fields["balance"].witness == "156,418,275.00"
    assert result.compared > 9  # a witness-only row counts against agreement


def test_two_amounts_in_one_cell_mark_the_row():
    page = [*PAGE, Word("1,250,000.00", CREDIT_X - 0.1, CREDIT_X - 0.002, 0.302, 0.312)]
    result = verify_statement_page(AI, page, page=1)
    assert "EXTRA_AMOUNT_IN_ROW" in result.rows[0].notes


def test_header_fields_are_found_on_their_page():
    words = [
        Word("Account", 0.5, 0.56, 0.1, 0.11),
        Word("9900004821", 0.6, 0.7, 0.1, 0.11),
        Word("OPENING", 0.1, 0.2, 0.2, 0.21),
        Word("184,048,975.00", 0.8, 0.9, 0.2, 0.21),
    ]
    found = verify_header(
        {
            "account_number": "9900 0048 21",
            "opening_balance": "184,048,975.00",
            "closing_balance": "1.00",
        },
        words,
    )
    assert found["account_number"].status == "AGREED"
    assert found["opening_balance"].status == "AGREED"
    assert found["closing_balance"].status == "SINGLE_SOURCE"


def test_a_serial_number_column_does_not_count_against_the_description():
    """Real statements print a cheque/serial number between description and debit; the reader
    leaves it out of the description, as it should."""
    page = [
        *_row(
            0.30, "16Aug", ["DEBITCARDTXN-DR", "123456 GRABRIDES-", "MY"], "12.40", None, "1,204.33"
        ),
        Word("3001234567", 0.45, 0.53, 0.30, 0.312),
    ]
    ai = [
        AiRow(0, "16 Aug", "DEBIT CARD TXN-DR\n123456 GRAB RIDES-\nMY", "12.40", None, "1,204.33")
    ]
    result = verify_statement_page(ai, page, page=7)
    assert result.rows[0].fields["description"].status == "AGREED"


def test_a_row_without_date_or_amounts_continues_the_previous_description():
    ai = [
        AiRow(0, "06/03/2026", "DEBIT CARD SWIFT COURIER", "355,200.00", None, "183,693,775.00"),
        AiRow(1, "", "SAME DAY PARCEL", None, None, None),
    ]
    result = verify_statement_page(ai, PAGE[4:8], page=1)
    assert len(result.rows) == 1
    assert result.rows[0].fields["description"].ai == "DEBIT CARD SWIFT COURIER\nSAME DAY PARCEL"


def test_a_page_starting_with_a_continuation_carries_it_to_the_previous_page():
    ai = [AiRow(0, "", "GREEN VALLEY FARMS", None, None, None), AI[0]]
    one_row = _row(
        0.30,
        "05/03/2026",
        ["TRANSFER IN HARBORVIEW HOTEL GROUP"],
        None,
        "32,100,000.00",
        "184,048,975.00",
    )
    result = verify_statement_page(ai, one_row, page=2)
    assert result.carry_over == "GREEN VALLEY FARMS"
    assert [r.source for r in result.rows] == ["AI"]


def test_printed_totals_below_the_last_row_are_not_row_values():
    """The last row's band once swallowed the totals line (real statement, last page)."""
    page = [
        *PAGE,
        Word("27,605,700.00", DEBIT_X - 0.1, DEBIT_X, 0.405, 0.417),
        Word("32,100,000.00", CREDIT_X - 0.1, CREDIT_X, 0.405, 0.417),
    ]
    result = verify_statement_page(AI, page, page=13, totals=["27,605,700.00", "32,100,000.00"])
    assert result.agreement == 1.0
    assert "EXTRA_AMOUNT_IN_ROW" not in result.rows[-1].notes
