"""E-LBL measurements (spec 016, T016-09, AC-016-10; docs/15 §5). Pure.

Over the labels a person checked: how often the AI's value was the person's, per task; per
confidence bucket of learning.v1.yaml, the mean confidence against the accuracy (a calibrated model
has a small gap); how many decided labels a later run disagreed with; and how many decided labels
lost the person's value (must be 0). On synthetic data the "person" is truth.json.
"""

from decimal import Decimal
from typing import Any

from app.domain.labels import Label


def _ratio(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0


def label_report(labels: list[Label], buckets: tuple[Decimal, ...]) -> dict[str, Any]:
    checked = [lb for lb in labels if lb.status in ("VERIFIED", "CORRECTED")]
    tasks: dict[str, dict[str, Any]] = {}
    for lb in checked:
        t = tasks.setdefault(lb.task, {"checked": 0, "agreed": 0})
        t["checked"] += 1
        t["agreed"] += int(lb.ai.value == lb.final_value)
    for t in tasks.values():
        t["agreement"] = _ratio(t["agreed"], t["checked"])
    edges = sorted(buckets)
    calibration = []
    scored = [lb for lb in checked if lb.ai.confidence is not None]
    lower = Decimal(0)
    for upper in edges:
        inside = [
            lb
            for lb in scored
            if lb.ai.confidence is not None
            and lower < lb.ai.confidence <= upper
            or (lower == 0 and lb.ai.confidence == 0)
        ]
        if inside:
            mean = float(sum((lb.ai.confidence or Decimal(0)) for lb in inside)) / len(inside)
            accuracy = _ratio(sum(1 for lb in inside if lb.ai.value == lb.final_value), len(inside))
            calibration.append(
                {
                    "from": str(lower),
                    "upTo": str(upper),
                    "labels": len(inside),
                    "meanConfidence": round(mean, 4),
                    "accuracy": accuracy,
                    "gap": round(abs(accuracy - mean), 4),
                }
            )
        lower = upper
    return {
        "checked": len(checked),
        "tasks": dict(sorted(tasks.items())),
        "calibration": calibration,
        "worstGap": max((b["gap"] for b in calibration), default=0.0),
        "unscored": len(checked) - len(scored),
        "disagreementsAfterRerun": sum(1 for lb in checked if lb.ai_disagrees_with_person),
        "personLabelsOverwritten": sum(1 for lb in checked if lb.final_source != "PERSON"),
    }
