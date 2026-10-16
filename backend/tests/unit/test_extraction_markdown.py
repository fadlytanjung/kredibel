"""The page as read, in Markdown (spec 016, T016-04, AC-016-4): document and page, reading method,
every value with both readings, the witness text; account and ID numbers masked. Synthetic only."""

from decimal import Decimal as D

from app.domain.accounts import mask_numbers_in_text
from app.domain.extraction_markdown import (
    PageExtraction,
    RecordReading,
    ValueReading,
    page_markdown,
)


def test_numbers_in_text_keep_amounts_and_dates_and_mask_account_and_id_numbers():
    text = "06/05 TRANSFER OUT ROASTLINE to MERIDIAN SAVINGS 0081234567720 24,500,000.00"
    assert (
        mask_numbers_in_text(text)
        == "06/05 TRANSFER OUT ROASTLINE to MERIDIAN SAVINGS ••••7720 24,500,000.00"
    )
    assert mask_numbers_in_text("NPWP 99.731.204.5-018.000") == "NPWP ••••8000"
    assert mask_numbers_in_text("Acc 1234 5678 9012 3456") == "Acc ••••3456"
    assert (
        mask_numbers_in_text("Saldo 24.500.000,00 on 2026-03-14")
        == "Saldo 24.500.000,00 on 2026-03-14"
    )
    assert mask_numbers_in_text("row 31, 2 pages, ref 1234567") == "row 31, 2 pages, ref 1234567"


def page(**kw) -> PageExtraction:
    base = dict(
        file_name="ACB_May_2026.pdf",
        page_no=1,
        page_count=3,
        doc_type="BANK_STATEMENT",
        type_confidence=D("0.97"),
        method="AI_TEXT_LAYER",
        agreement=D("0.99"),
        model="gemini-2.5-flash",
        prompt_version="read_page v3",
        records=[
            RecordReading(
                title="Row 6",
                values=[
                    ValueReading("date", "AGREED", "06/05", "06/05"),
                    ValueReading(
                        "description",
                        "AGREED",
                        "TRANSFER OUT ROASTLINE EQUIPMENT | to 0081234567720",
                        "TRANSFER OUT ROASTLINE EQUIPMENT",
                    ),
                    ValueReading("amount", "CONFLICT", "24,500,000.00", "24,580,000.00"),
                    ValueReading("balance", "SINGLE_SOURCE", "31,940,000.00", None),
                ],
            )
        ],
        witness_text=(
            "06/05 TRANSFER OUT ROASTLINE EQUIPMENT\n"
            "to MERIDIAN SAVINGS 0081234567720 24,500,000.00"
        ),
    )
    return PageExtraction(**{**base, **kw})


def test_ac016_4_the_page_markdown_states_what_was_read_and_how():
    md = page_markdown(page())
    lines = md.splitlines()
    assert lines[0] == "# ACB_May_2026.pdf, page 1 of 3"
    assert "Document type: BANK_STATEMENT (0.97)" in lines
    assert "Page type: not classified yet" in lines
    assert (
        "Reading: AI_TEXT_LAYER, agreement 0.99, model gemini-2.5-flash, prompt read_page v3"
        in lines
    )
    assert "| Record | Field | Readings | Model | Text layer |" in lines
    assert "| Row 6 | amount | conflict | 24,500,000.00 | 24,580,000.00 |" in lines
    assert "| Row 6 | balance | one reading | 31,940,000.00 | — |" in lines
    # A pipe inside a value never breaks the table; numbers are masked in values and witness text.
    assert (
        "| Row 6 | description | agreed | TRANSFER OUT ROASTLINE EQUIPMENT \\| to ••••7720 "
        "| TRANSFER OUT ROASTLINE EQUIPMENT |" in lines
    )
    assert "0081234567720" not in md
    assert md.count("```") == 2 and "to MERIDIAN SAVINGS ••••7720 24,500,000.00" in md
    assert md.endswith("\n")


def test_ac016_4_a_page_without_values_or_text_layer_says_so():
    md = page_markdown(
        page(
            records=[],
            witness_text="",
            method="AI_ONLY",
            agreement=None,
            type_confidence=None,
            model=None,
            prompt_version=None,
        )
    )
    assert "Document type: BANK_STATEMENT" in md.splitlines()
    assert "Reading: AI_ONLY" in md.splitlines()
    assert "No values were read on this page." in md
    assert "No text layer or OCR words on this page; it was read from its image only." in md
