"""Verified examples for the prompts (spec 016, AC-016-9; ADR-016). Pure.

A label a person decided carries an embedding of its text. Before a model call, the nearest
decided labels of the same task are offered as examples: from this workspace only (any other is
rejected and counted), at least the policy's similarity, best first, at most the policy's number.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    org_id: str
    label_id: str
    task: str
    text: str
    value: str
    similarity: float


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


def choose_examples(
    org_id: str, candidates: list[Example], *, limit: int, min_similarity: float
) -> tuple[list[Example], int]:
    """(examples to show, examples rejected because they came from another workspace)."""
    rejected = sum(1 for c in candidates if c.org_id != org_id)
    best: dict[str, Example] = {}
    for c in candidates:
        if c.org_id != org_id or c.similarity < min_similarity:
            continue
        kept = best.get(c.label_id)
        if kept is None or c.similarity > kept.similarity:
            best[c.label_id] = c
    ordered = sorted(best.values(), key=lambda e: (-e.similarity, e.label_id))
    return ordered[:limit], rejected


def as_prompt_rows(task: str, examples: list[Example]) -> list[dict[str, str]]:
    """What the model sees of each example: the text a person decided on and their answer."""
    key = "category" if task == "CATEGORY" else "doc_type"
    text_key = "description" if task == "CATEGORY" else "page1_text"
    return [{text_key: e.text, key: e.value} for e in examples]
