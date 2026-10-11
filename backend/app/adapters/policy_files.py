"""Read the YAML contracts (plans, policy) from disk and hand them to the pure domain parsers.

Normative reference: spec 013 plan (adapters/policy_files.py), AC-013-5.
"""

from pathlib import Path

import yaml

from app.domain.plans import PlanCatalog, parse_plans


def load_plans(path: Path) -> PlanCatalog:
    """Load and validate contracts/plans.v1.yaml; any problem raises and stops start-up."""
    with path.open(encoding="utf-8") as handle:
        return parse_plans(yaml.safe_load(handle))
