"""Grounding: every value the reader returns must be in the chunk it cites (ADR-023, docs/07 §6)."""

from app.domain.layout import chunk_page
from app.domain.verify import AiRow, ground_statement_page
from tests.unit.test_verify_statement import AI, CREDIT_X, PAGE, Word, _row

CHUNKS = chunk_page(PAGE, page=1)
ROWS = [c for c in CHUNKS if c.kind == "TABLE_ROW"]


def _cited(rows=AI):
    return [r._replace(chunk_ids=(ROWS[i].id,)) for i, r in enumerate(rows)]


def test_values_found_in_their_cited_chunk_are_grounded():
    result = ground_statement_page(_cited(), CHUNKS, page=1)
    assert result.agreement == 1.0
    assert result.rows[0].fields["credit"].bbox is not None
    assert result.rows[0].fields["credit"].bbox.x1 == CREDIT_X
    assert result.rows[0].chunk_ids == (ROWS[0].id,)


def test_a_value_missing_from_its_chunk_is_a_conflict():
    rows = _cited()
    rows[0] = rows[0]._replace(credit_text="7,250,000.00")
    result = ground_statement_page(rows, CHUNKS, page=1)
    credit = result.rows[0].fields["credit"]
    assert (credit.status, credit.witness) == ("CONFLICT", "32,100,000.00")


def test_rows_without_citations_are_assigned_by_date_in_order():
    result = ground_statement_page(list(AI), CHUNKS, page=1)
    assert [r.chunk_ids for r in result.rows] == [(c.id,) for c in ROWS]
    assert result.agreement == 1.0


def test_a_row_chunk_nobody_cites_is_a_witness_only_row():
    page = [*PAGE, *_row(0.42, "10/03/2026", ["ADMIN FEE"], "25,000.00", None, "156,418,275.00")]
    chunks = chunk_page(page, page=1)
    result = ground_statement_page(_cited(), chunks, page=1)
    assert [r.source for r in result.rows] == ["AI", "AI", "AI", "WITNESS"]
    assert result.rows[3].fields["debit"].witness == "25,000.00"
    assert result.agreement < 1.0


def test_what_the_image_shows_differently_from_the_text_is_a_conflict():
    """A covered value: the text layer holds the old number, the reader reports the visible one."""
    rows = _cited()
    rows[0] = rows[0]._replace(credit_text="37,100,000.00", differs_from_text=("credit",))
    result = ground_statement_page(rows, CHUNKS, page=1)
    assert result.rows[0].fields["credit"].status == "CONFLICT"
    assert "VISIBLE_DIFFERS_FROM_TEXT" in result.rows[0].notes


def test_a_row_without_any_chunk_is_ungrounded():
    rows = [*_cited(), AiRow(9, "11/03/2026", "ATM WITHDRAWAL", "500,000.00", None, "1.00")]
    result = ground_statement_page(rows, CHUNKS, page=1)
    last = result.rows[-1]
    assert "UNGROUNDED" in last.notes and last.fields["debit"].status == "SINGLE_SOURCE"


def test_continuations_still_join_the_row_above():
    rows = [*_cited(), AiRow(3, "", "SAME DAY PARCEL", None, None, None)]
    result = ground_statement_page(rows, CHUNKS, page=1)
    assert len(result.rows) == 3
    description = result.rows[2].fields["description"].ai
    assert description is not None and description.endswith("SAME DAY PARCEL")


def test_a_cell_with_two_amounts_is_marked():
    page = [*PAGE, Word("1,250,000.00", CREDIT_X - 0.1, CREDIT_X - 0.002, 0.302, 0.312)]
    chunks = chunk_page(page, page=1)
    result = ground_statement_page(list(AI), chunks, page=1)
    assert "EXTRA_AMOUNT_IN_ROW" in result.rows[0].notes
