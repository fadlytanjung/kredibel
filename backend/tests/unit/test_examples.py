"""Verified examples (spec 016, T016-08, AC-016-9): same workspace only, similarity floor from the
policy, best first, deduplicated, at most the policy's number. Synthetic texts only."""

import asyncio

from app.domain.examples import Example, as_prompt_rows, choose_examples, cosine
from tests.fakes.embedder import FakeEmbedder


def ex(label: str, sim: float, org: str = "org_1", value: str = "INVENTORY_PURCHASE") -> Example:
    return Example(org, label, "CATEGORY", f"TRANSFER OUT {label}", value, sim)


def test_ac016_9_only_this_workspace_above_the_floor_best_first_at_most_the_limit():
    candidates = [
        ex("lbl_a", 0.91),
        ex("lbl_b", 0.79),  # below the floor
        ex("lbl_c", 0.97, org="org_other"),  # another workspace: rejected
        ex("lbl_d", 0.85),
        ex("lbl_a", 0.88),  # the same label twice: its best similarity counts
        ex("lbl_e", 0.99),
    ]
    chosen, rejected = choose_examples("org_1", candidates, limit=2, min_similarity=0.80)
    assert [c.label_id for c in chosen] == ["lbl_e", "lbl_a"]
    assert rejected == 1
    assert all(c.org_id == "org_1" for c in chosen)
    chosen, _ = choose_examples("org_1", candidates, limit=5, min_similarity=0.80)
    assert [c.label_id for c in chosen] == ["lbl_e", "lbl_a", "lbl_d"]


def test_the_prompt_sees_the_decided_text_and_the_answer_only():
    rows = as_prompt_rows("CATEGORY", [ex("lbl_a", 0.9)])
    assert rows == [{"description": "TRANSFER OUT lbl_a", "category": "INVENTORY_PURCHASE"}]
    doc = Example("org_1", "lbl_x", "DOC_TYPE", "INVOICE No 12", "PURCHASE_INVOICE", 0.9)
    assert as_prompt_rows("DOC_TYPE", [doc]) == [
        {"page1_text": "INVOICE No 12", "doc_type": "PURCHASE_INVOICE"}
    ]


def test_the_fake_embedder_puts_texts_with_shared_words_close():
    a, b, c = asyncio.run(
        FakeEmbedder().embed(
            [
                "TRANSFER OUT GREEN VALLEY FARMS 0912",
                "TRANSFER OUT GREEN VALLEY FARMS 1003",
                "PAYROLL JUNE STAFF",
            ]
        )
    )
    assert cosine(a, b) > 0.95 and cosine(a, c) < 0.2
