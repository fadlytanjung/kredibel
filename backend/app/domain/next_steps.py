"""Deterministic next steps catalog lookup and ordering (spec 008, AC-008-4; docs/08 §8). Pure."""

from collections.abc import Sequence

from app.domain.findings import Finding
from app.domain.risk import RiskPolicy


def next_steps_for_findings(findings: Sequence[Finding], policy: RiskPolicy) -> list[str]:
    """Return unique next steps from policy catalog for live findings (AC-008-4)."""
    live = [f for f in findings if f.status in ("OPEN", "ACKNOWLEDGED")]
    live_sorted = sorted(live, key=lambda f: f.severity_rank)

    seen: set[str] = set()
    steps: list[str] = []

    for f in live_sorted:
        # 1. Exact match on finding code
        step = policy.next_steps.get(f.code)
        if not step:
            # 2. Match on prefix (e.g. A01 matches A01_RUNNING_BALANCE_BREAK)
            prefix = f.code.split("_")[0]
            for k, v in policy.next_steps.items():
                if k == prefix or k.startswith(f"{prefix}_"):
                    step = v
                    break

        if step and step not in seen:
            seen.add(step)
            steps.append(step)

    return steps
