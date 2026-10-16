"""What a person expects against what the documents show (spec 024, AC-024-5): within the tolerance
it is as expected, otherwise the difference is shown; a month not reconciled yet is waiting. It
never says the expectation is wrong. Synthetic data only."""

from decimal import Decimal as D

from app.domain.expectations import Actual, Expectation, compare_expectations

TOLERANCE = D("0.05")


def test_ac024_5_each_month_and_direction_is_as_expected_different_or_waiting():
    expected = [
        Expectation("2026-08", money_in=D("160000000"), money_out=D("120000000")),
        Expectation("2026-09", money_in=D("150000000"), money_out=None),
        Expectation("2026-11", money_in=D("10000000"), money_out=D("5000000")),
    ]
    actual = {
        "2026-08": Actual("2026-08", D("160423200.00"), D("152306418.00"), reconciled=True),
        "2026-09": Actual("2026-09", D("155670450.00"), D("161074392.00"), reconciled=False),
    }

    aug, sep, nov = compare_expectations(expected, actual, TOLERANCE)

    assert aug.money_in is not None and aug.money_in.status == "AS_EXPECTED"
    assert aug.money_out is not None and aug.money_out.status == "DIFFERENT"
    assert aug.money_out.difference == D("32306418.00")
    assert sep.money_in is not None and sep.money_in.status == "WAITING" and sep.money_out is None
    assert nov.money_in is not None and nov.money_in.status == "WAITING"
    assert nov.money_in.actual is None
