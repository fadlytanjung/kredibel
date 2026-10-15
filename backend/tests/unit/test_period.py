"""A dashboard period and the previous one of equal length (spec 010, AC-010-1)."""

import pytest

from app.domain.period import resolve_period

DATA = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]


def test_a_month_a_quarter_a_year_and_a_range_with_their_previous_periods():
    month = resolve_period("2026-03", DATA)
    assert (month.months, month.previous) == (("2026-03",), ("2026-02",))
    quarter = resolve_period("2026-Q1", DATA)
    assert quarter.months == ("2026-01", "2026-02", "2026-03")
    assert quarter.previous == ("2025-10", "2025-11", "2025-12")
    year = resolve_period("2026", DATA)
    assert year.months[0] == "2026-01" and year.months[-1] == "2026-12" and len(year.previous) == 12
    span = resolve_period("2025-12..2026-02", DATA)
    assert span.months == ("2025-12", "2026-01", "2026-02")
    assert span.previous == ("2025-09", "2025-10", "2025-11")


def test_all_is_every_month_with_data_and_has_no_previous_period():
    every = resolve_period("all", DATA)
    assert every.months == tuple(DATA) and every.previous == ()
    assert resolve_period("all", []).months == ()


def test_recent_is_the_last_three_months_with_data():
    recent = resolve_period("recent", DATA)
    assert recent.months == ("2026-01", "2026-02", "2026-03")
    assert recent.previous == ("2025-10", "2025-11", "2025-12")


def test_hint_formatted_and_messy_period_strings_resolve_cleanly():
    assert resolve_period("month (2026-03)", DATA).months == ("2026-03",)
    assert resolve_period("quarter (2026-Q1)", DATA).months == ("2026-01", "2026-02", "2026-03")
    assert resolve_period("year (2026)", DATA).months[0] == "2026-01"
    assert resolve_period("range (2025-12..2026-02)", DATA).months == (
        "2025-12",
        "2026-01",
        "2026-02",
    )
    assert resolve_period("  2026-03  ", DATA).months == ("2026-03",)


@pytest.mark.parametrize("bad", ["2026-13", "2026-Q5", "2026-03..2026-01", "March", ""])
def test_anything_else_is_refused(bad):
    with pytest.raises(ValueError):
        resolve_period(bad, DATA)

