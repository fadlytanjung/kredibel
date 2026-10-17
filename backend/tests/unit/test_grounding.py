"""Unit tests for Grounding Guard (spec 008, AC-008-5; docs/06 §5.1; docs/15 §4). Pure."""

from decimal import Decimal

import pytest

from app.domain.findings import Finding
from app.domain.grounding import (
    GroundingContext,
    check_grounding,
)


@pytest.fixture
def sample_context():
    return GroundingContext(
        facts={
            "2026-03:money_in": Decimal("231400000"),
            "2026-03:closing": Decimal("60400000"),
            "2026-03:single_payout": Decimal("1250000"),
            "2026-03:rate": Decimal("64"),
        },
        findings={
            "fnd_a01": Finding(
                finding_id="fnd_a01",
                code="A01_RUNNING_BALANCE_BREAK",
                category="ARITHMETIC",
                severity="CRITICAL",
                title="Balance break",
                facts={"diff": "6000000", "printed": "42500000", "expected": "48500000"},
                evidence=[],
            )
        },
        documents={"doc_1", "doc_2"},
        matches={"mat_1"},
    )


class TestGroundingGuardTDD:
    """T008-03: Grounding Guard rules, marker resolution, and number normalization (AC-008-5)."""

    def test_ac008_5_valid_text_with_exact_citations_passes(self, sample_context):
        text = (
            "Money in reached IDR 231,400,000 [[fact:2026-03:money_in]]. "
            "A balance break was detected [[finding:fnd_a01]]."
        )
        res = check_grounding(text, sample_context)
        assert res.valid is True
        assert len(res.problems) == 0
        assert len(res.citations) == 2
        assert res.citations[0].kind == "fact"
        assert res.citations[0].id == "2026-03:money_in"
        assert res.citations[1].kind == "finding"
        assert res.citations[1].id == "fnd_a01"

    def test_ac008_5_a_month_written_as_a_date_is_not_a_number(self, sample_context):
        """Spec 024: "Month 2026-10 Reconciliation" in a link is a date; its "10" needs no source,
        while an uncited amount in the same sentence still does."""
        text = (
            "Money in reached IDR 231,400,000 [[fact:2026-03:money_in]]. "
            "See the [Month 2026-10 Reconciliation](/months/2026-10) page, opened 2026-10-17."
        )
        assert check_grounding(text, sample_context).valid is True
        res = check_grounding("The 2026-10 month lost 75,000 to fees.", sample_context)
        assert res.valid is False

    def test_ac008_5_unresolved_marker_fails(self, sample_context):
        text = "Revenue was strong [[fact:2026-03:unknown_metric]]."
        res = check_grounding(text, sample_context)
        assert res.valid is False
        assert any("Unresolved marker" in p for p in res.problems)

    def test_ac008_5_various_number_formats_match_cited_facts(self, sample_context):
        # IDR 1,250,000, IDR 1.25 million, 1,250,000, 64% all match their facts
        cases = [
            ("The single payout was IDR 1,250,000 [[fact:2026-03:single_payout]]."),
            ("The single payout was IDR 1.25 million [[fact:2026-03:single_payout]]."),
            ("The single payout was 1,250,000 [[fact:2026-03:single_payout]]."),
            ("The match rate reached 64% [[fact:2026-03:rate]]."),
        ]
        for sentence in cases:
            res = check_grounding(sentence, sample_context)
            assert res.valid is True, f"Failed for sentence: {sentence}, problems: {res.problems}"

    def test_ac008_5_a_signed_fact_matches_its_number_with_or_without_the_sign(self):
        """A01 records the break as a signed difference; the sentence names its size (T008-03)."""
        context = GroundingContext(
            findings={
                "fnd_neg": Finding(
                    finding_id="fnd_neg",
                    code="A01_RUNNING_BALANCE_BREAK",
                    category="ARITHMETIC",
                    severity="CRITICAL",
                    title="Balance break",
                    facts={"difference": "-6000000.00"},
                    evidence=[],
                )
            },
        )
        for text in (
            "The balance breaks by -6,000,000.00 [[finding:fnd_neg]].",
            "The balance is IDR 6,000,000 short [[finding:fnd_neg]].",
        ):
            assert check_grounding(text, context).valid, text
        assert not check_grounding("It is 7,000,000 short [[finding:fnd_neg]].", context).valid

    def test_ac008_5_ambiguous_suffix_m_is_rejected(self, sample_context):
        # 1.25M is rejected as ambiguous (must use 'million' or explicit number)
        text = "The single payout was IDR 1.25M [[fact:2026-03:single_payout]]."
        res = check_grounding(text, sample_context)
        assert res.valid is False
        assert any("ambiguous" in p.lower() for p in res.problems)

    def test_ac008_5_uncited_number_fails_quoting_sentence(self, sample_context):
        # An unmatched number fails with the sentence quoted
        text = "The company recorded an unverified bonus of IDR 99,000,000 without explanation."
        res = check_grounding(text, sample_context)
        assert res.valid is False
        assert any("99,000,000" in p for p in res.problems)
        assert any("unverified bonus" in p for p in res.problems)

    def test_ac008_5_dates_and_ordinals_do_not_require_citations(self, sample_context):
        text = "On 14 March 2026, the statement was inspected on page 2 [[doc:doc_1#p2]]."
        res = check_grounding(text, sample_context)
        assert res.valid is True
        assert len(res.problems) == 0

    def test_ac008_5_turn_scoped_assistant_facts_validated(self, sample_context):
        context_with_turn = GroundingContext(
            facts={"fact:q_abc:bank_total": Decimal("5000000")},
            allowed_fact_prefixes=("fact:q_abc:",),
        )
        valid_text = "The total queried was IDR 5,000,000 [[fact:q_abc:bank_total]]."
        res = check_grounding(valid_text, context_with_turn)
        assert res.valid is True

        # Using a foreign turn fact fails
        foreign_text = "The total was IDR 5,000,000 [[fact:q_other:bank_total]]."
        res_foreign = check_grounding(foreign_text, context_with_turn)
        assert res_foreign.valid is False
