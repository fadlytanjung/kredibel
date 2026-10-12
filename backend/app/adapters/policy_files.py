"""Read the YAML contracts (plans, policy) from disk and hand them to the pure domain parsers.

Normative reference: spec 013 plan (adapters/policy_files.py), AC-013-5.
"""

from pathlib import Path

import yaml

from app.domain.categorize import CategoryPolicy, parse_category_policy
from app.domain.checks.policy import ForensicsPolicy, parse_forensics
from app.domain.plans import PlanCatalog, parse_plans


def load_plans(path: Path) -> PlanCatalog:
    """Load and validate contracts/plans.v1.yaml; any problem raises and stops start-up."""
    with path.open(encoding="utf-8") as handle:
        return parse_plans(yaml.safe_load(handle))


def load_forensics(policy_dir: Path) -> ForensicsPolicy:
    """forensics.v1.yaml with the next steps of risk.v1.yaml (docs/08 §2–§3)."""
    with (policy_dir / "forensics.v1.yaml").open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    with (policy_dir / "risk.v1.yaml").open(encoding="utf-8") as handle:
        steps = (yaml.safe_load(handle) or {}).get("nextSteps") or {}
    return parse_forensics(raw, steps)


def load_category_policy(categories_file: Path, policy_dir: Path) -> CategoryPolicy:
    """categories.v1.yaml and categorization-rules.v1.yaml (docs/08 §4.1)."""
    with categories_file.open(encoding="utf-8") as handle:
        categories = yaml.safe_load(handle)
    with (policy_dir / "categorization-rules.v1.yaml").open(encoding="utf-8") as handle:
        rules = yaml.safe_load(handle)
    return parse_category_policy(categories, rules)
