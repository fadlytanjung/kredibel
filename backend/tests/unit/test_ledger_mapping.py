"""Ledger column mapping (spec 005, T005-11; AC-005-11, AC-005-12): the proposal from the header
and value shapes, the parse with a confirmed mapping, the sample rows a person checks, and the
validation of what a person sends back. Synthetic layouts only (docs/18)."""

from datetime import date
from decimal import Decimal

from app.domain.ledger_parse import (
    LedgerMapping,
    compute_layout_signature,
    is_auto_confirmable,
    parse_ledger_content,
    propose_mapping,
    read_table,
    sample_rows,
)
from app.domain.review_items import confirm_mapping_item

STANDARD = """Date,Journal,Account,Account Name,Description,Reference,Debit,Credit
10/03/2026,BNK-001,6050,Rent,Office Rent,,1000000.00,
10/03/2026,BNK-001,1110,Bank,Office Rent,,,1000000.00
"""

# An Indonesian accounting package: local headers, day-first dates, a dot for thousands and a
# comma for the decimals. Nothing in the parser's English synonyms recognizes it by itself.
INDONESIAN = """Tanggal;Keterangan;Kode Akun;Nama Akun;Debet;Kredit
02/03/2026;Penjualan kopi;4000;Penjualan;0,00;120.000.000,00
02/03/2026;Penjualan kopi;1110;Bank;120.000.000,00;0,00
03/03/2026;Sewa gudang;6050;Sewa;15.000.000,00;0,00
03/03/2026;Sewa gudang;1110;Bank;0,00;15.000.000,00
15/03/2026;Gaji;6100;Gaji;18.000.000,00;0,00
15/03/2026;Gaji;1110;Bank;0,00;18.000.000,00
"""

SIGNED_CREDIT_POSITIVE = """Tgl,Uraian,No Akun,Nominal
2026-03-02,Penjualan kopi,4000,120000000.00
2026-03-02,Penjualan kopi,1110,-120000000.00
"""


def test_ac005_11_a_standard_english_layout_is_proposed_complete_and_auto_confirmed():
    headers, rows = read_table(STANDARD)
    proposal = propose_mapping(headers, rows)
    assert proposal.complete
    assert (proposal.date, proposal.description, proposal.account_code) == (
        "Date",
        "Description",
        "Account",
    )
    assert (proposal.debit, proposal.credit, proposal.amount) == ("Debit", "Credit", None)
    assert proposal.account_name == "Account Name" and proposal.reference == "Reference"
    assert (proposal.date_format, proposal.decimal_separator) == ("DD/MM/YYYY", ".")
    assert is_auto_confirmable(proposal, headers)


def test_ac005_11_an_indonesian_layout_is_proposed_from_shapes_but_needs_a_person():
    headers, rows = read_table(INDONESIAN)
    assert headers == ["Tanggal", "Keterangan", "Kode Akun", "Nama Akun", "Debet", "Kredit"]
    proposal = propose_mapping(headers, rows)
    assert proposal.complete
    assert (proposal.date, proposal.description, proposal.account_code) == (
        "Tanggal",
        "Keterangan",
        "Kode Akun",
    )
    assert (proposal.account_name, proposal.debit, proposal.credit) == (
        "Nama Akun",
        "Debet",
        "Kredit",
    )
    # Day-first dates and a decimal comma, read from the values' shapes, never from the words.
    assert proposal.date_format == "DD/MM/YYYY"
    assert proposal.decimal_separator == ","
    assert not is_auto_confirmable(proposal, headers), "a new layout is confirmed by a person"


def test_ac005_12_the_confirmed_mapping_parses_every_row_in_minor_units_and_months():
    headers, rows = read_table(INDONESIAN)
    mapping = propose_mapping(headers, rows)
    result = parse_ledger_content(INDONESIAN, doc_id="doc_gl", currency="IDR", mapping=mapping)
    assert result.bad_rows == [] and not result.too_many_bad_rows
    assert len(result.rows) == 6
    first = result.rows[0]
    assert (first.date, first.account_code, first.account_name) == (
        date(2026, 3, 2),
        "4000",
        "Penjualan",
    )
    assert (first.debit, first.credit) == (Decimal("0.00"), Decimal("120000000.00"))
    assert result.rows[2].debit == Decimal("15000000.00")
    assert result.layout_signature == compute_layout_signature(headers)
    assert {r.date.strftime("%Y-%m") for r in result.rows} == {"2026-03"}


def test_ac005_11_a_signed_amount_column_follows_the_sign_convention():
    headers, rows = read_table(SIGNED_CREDIT_POSITIVE)
    proposal = propose_mapping(headers, rows)
    assert (proposal.amount, proposal.debit, proposal.credit) == ("Nominal", None, None)
    assert proposal.date_format == "YYYY-MM-DD" and proposal.sign_convention == "DEBIT_POSITIVE"
    debit_positive = parse_ledger_content(SIGNED_CREDIT_POSITIVE, doc_id="d", mapping=proposal)
    assert (debit_positive.rows[0].debit, debit_positive.rows[0].credit) == (
        Decimal("120000000.00"),
        Decimal("0"),
    )
    flipped = LedgerMapping.from_dict({**proposal.to_dict(), "signConvention": "CREDIT_POSITIVE"})
    credit_positive = parse_ledger_content(SIGNED_CREDIT_POSITIVE, doc_id="d", mapping=flipped)
    assert (credit_positive.rows[0].debit, credit_positive.rows[0].credit) == (
        Decimal("0"),
        Decimal("120000000.00"),
    )


def test_ac005_11_five_sample_rows_show_what_the_proposal_reads_and_what_it_cannot():
    headers, rows = read_table(INDONESIAN)
    mapping = propose_mapping(headers, rows)
    samples = sample_rows(INDONESIAN, mapping, currency="IDR")
    assert len(samples) == 5
    assert samples[0]["raw"] == [
        "02/03/2026",
        "Penjualan kopi",
        "4000",
        "Penjualan",
        "0,00",
        "120.000.000,00",
    ]
    assert samples[0]["parsed"] == {
        "date": "2026-03-02",
        "accountCode": "4000",
        "description": "Penjualan kopi",
        "debit": {"amount": "0.00", "currency": "IDR"},
        "credit": {"amount": "120000000.00", "currency": "IDR"},
    }
    assert samples[0]["error"] is None
    # A wrong column choice is visible at once: the date column read as the amount.
    wrong = LedgerMapping.from_dict({**mapping.to_dict(), "debit": "Tanggal"})
    assert sample_rows(INDONESIAN, wrong, currency="IDR")[0]["error"]


def test_ac005_11_a_mapping_a_person_sends_back_is_validated_before_anything_is_parsed():
    assert LedgerMapping.from_dict({}).problems() == [
        "date: choose the column",
        "description: choose the column",
        "accountCode: choose the column",
        "amounts: choose a debit and a credit column, or one amount column",
    ]
    both = LedgerMapping.from_dict(
        {
            "date": "Date",
            "description": "Memo",
            "accountCode": "Account",
            "debit": "Debit",
            "credit": "Credit",
            "amount": "Net",
        }
    )
    assert both.problems() == ["amounts: choose a debit and a credit column, or one amount column"]
    odd = LedgerMapping.from_dict(
        {
            "date": "Date",
            "description": "Memo",
            "accountCode": "Account",
            "amount": "Net",
            "dateFormat": "YY/MM",
            "decimalSeparator": ";",
        }
    )
    assert odd.problems() == ["dateFormat: unknown format", "decimalSeparator: must be '.' or ','"]
    good = LedgerMapping.from_dict(
        {"date": "Date", "description": "Memo", "accountCode": "Account", "amount": "Net"}
    )
    assert good.complete and good.to_dict()["signConvention"] == "DEBIT_POSITIVE"


def test_ac005_11_the_model_fills_only_what_code_missed_and_only_with_real_columns():
    from app.domain.ledger_parse import merge_model_proposal
    from app.domain.reading import LedgerMappingProposal

    headers = ["Tanggal", "Uraian Transaksi", "Kode Akun", "Nama Akun", "Debet", "Kredit"]
    code = propose_mapping(
        headers, [["02/03/2026", "Penjualan kopi", "4000", "Penjualan", "0,00", "1.000,00"]]
    )
    assert not code.complete and code.description == ""
    model = LedgerMappingProposal(
        description="uraian transaksi",  # a header code's synonyms do not know, case-insensitive
        date="Keterangan",  # code already chose Tanggal: ignored
        reference="Nomor Bukti",  # not in the header: ignored
        decimal_separator=".",  # code read a comma from the shapes: kept
        confidence=0.8,
    )
    merged = merge_model_proposal(code, model, headers)
    assert merged.complete
    assert merged.description == "Uraian Transaksi" and merged.date == "Tanggal"
    assert merged.reference is None and merged.decimal_separator == ","
    assert merge_model_proposal(code, LedgerMappingProposal(), headers) == code

    signed = propose_mapping(
        ["Tgl", "Memo", "Akun", "Nilai"], [["2026-03-02", "x", "4000", "-5.00"]]
    )
    assert signed.amount == "Nilai" and signed.sign_convention == "DEBIT_POSITIVE"
    flipped = merge_model_proposal(
        LedgerMapping.from_dict({**signed.to_dict(), "amount": None, "signConvention": None}),
        LedgerMappingProposal(amount="Nilai", sign_convention="CREDIT_POSITIVE"),
        ["Tgl", "Memo", "Akun", "Nilai"],
    )
    assert (flipped.amount, flipped.sign_convention) == ("Nilai", "CREDIT_POSITIVE")


def test_ac005_11_the_review_item_names_the_file_and_carries_the_proposal_and_sample_rows():
    headers, rows = read_table(INDONESIAN)
    mapping = propose_mapping(headers, rows)
    item = confirm_mapping_item(
        "doc_gl",
        "GL_2026_Q1.csv",
        mapping=mapping.to_dict(),
        header=headers,
        sample_rows=rows[:5],
        layout_signature="sig_1",
    )
    assert item.kind == "CONFIRM_LEDGER_MAPPING" and item.month is None and item.doc_id == "doc_gl"
    assert item.item_id.startswith("itm_") and item.allowed_actions == ["CONFIRM_MAPPING"]
    assert item.title == "Check the columns of GL_2026_Q1.csv"
    assert item.subject.doc_ids == ["doc_gl"]
    assert item.suggestion.mapping == {
        "layoutSignature": "sig_1",
        "mapping": mapping.to_dict(),
        "header": headers,
        "sampleRows": rows[:5],
        "badRows": [],
    }
    reopened = confirm_mapping_item(
        "doc_gl",
        "GL_2026_Q1.csv",
        mapping=mapping.to_dict(),
        header=headers,
        sample_rows=rows[:5],
        bad_rows=[3, 4, 5],
    )
    assert reopened.item_id == item.item_id, "the same item reopens, never a second one"
    assert reopened.title == "3 rows of GL_2026_Q1.csv could not be read: check the columns"
