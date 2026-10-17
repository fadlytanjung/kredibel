"""The assistant's money-flow mini chart (spec 011, AC-011-4): each month's bar is its money in and
out against the busiest month's, so a month with no money (a month opened by a late invoice) draws
none. Synthetic data only."""

from types import SimpleNamespace

from app.services.assistant_service import flow_rows


def month(key: str, money_in: str, money_out: str) -> SimpleNamespace:
    return SimpleNamespace(
        month=key, figures={"moneyIn": {"value": money_in}, "moneyOut": {"value": money_out}}
    )


def test_bars_follow_each_months_money():
    rows = flow_rows(
        [
            month("2026-09", "817318550.00", "848158294.00"),
            month("2026-07", "0", "0"),
            month("2026-10", "1026805950.00", "705933026.00"),
            month("2026-08", "850089760.00", "594921934.00"),
        ]
    )
    assert [(r[0], r[2]) for r in rows] == [
        ("2026-07", "0%"),
        ("2026-08", "83%"),
        ("2026-09", "96%"),
        ("2026-10", "100%"),
    ]
    assert rows[3][1] == "In: 1,026,805,950 | Out: 705,933,026"


def test_no_money_at_all_draws_no_bars():
    assert flow_rows([month("2026-07", "0", "0")]) == [["2026-07", "In: 0 | Out: 0", "0%"]]
