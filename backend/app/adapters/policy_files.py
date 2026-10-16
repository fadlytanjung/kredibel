"""Read the YAML contracts (plans, policy) from disk and hand them to the pure domain parsers.

Normative reference: spec 013 plan (adapters/policy_files.py), AC-013-5.
"""

from decimal import Decimal
from pathlib import Path

import yaml

from app.domain.categorize import CategoryPolicy, parse_category_policy
from app.domain.checks.policy import ForensicsPolicy, parse_forensics
from app.domain.labels import LearningPolicy
from app.domain.plans import PlanCatalog, parse_plans
from app.domain.profit_loss import ProfitLossPolicy
from app.domain.reconciliation_policy import ReconciliationPolicy
from app.domain.risk import RiskPolicy, parse_risk_policy


def load_plans(path: Path) -> PlanCatalog:
    """Load and validate contracts/plans.v1.yaml; any problem raises and stops start-up."""
    with path.open(encoding="utf-8") as handle:
        return parse_plans(yaml.safe_load(handle))


def load_risk_policy(policy_dir: Path) -> RiskPolicy:
    """risk.v1.yaml with fraud risk levels, weights and next steps (spec 008, docs/08 §8)."""
    with (policy_dir / "risk.v1.yaml").open(encoding="utf-8") as handle:
        return parse_risk_policy(yaml.safe_load(handle) or {})


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


def load_reconciliation_policy(policy_dir: Path) -> ReconciliationPolicy:
    """Validate all scoring thresholds from reconciliation.v1.yaml (AC-007-17)."""
    with (policy_dir / "reconciliation.v1.yaml").open(encoding="utf-8") as handle:
        return ReconciliationPolicy.model_validate(yaml.safe_load(handle))


def load_profit_loss_policy(policy_dir: Path) -> ProfitLossPolicy:
    with (policy_dir / "profit-loss.v1.yaml").open(encoding="utf-8") as handle:
        return ProfitLossPolicy.model_validate(yaml.safe_load(handle))


def load_learning_policy(policy_dir: Path) -> LearningPolicy:
    """contracts/policy/learning.v1.yaml (spec 016): thresholds per task and the dataset split."""
    with (policy_dir / "learning.v1.yaml").open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    examples = raw.get("examples") or {}
    dataset = raw.get("dataset") or {}
    return LearningPolicy(
        needs_check_below={
            k: Decimal(str(v)) for k, v in (raw.get("needsCheckBelow") or {}).items()
        },
        eval_share=Decimal(str(dataset.get("evalShare", "0.20"))),
        examples_per_call=int(examples.get("perCall", 5)),
        min_similarity=Decimal(str(examples.get("minSimilarity", "0.80"))),
        remembered_corrections=bool((raw.get("rememberedCorrections") or {}).get("enabled", True)),
        examples_enabled=bool(examples.get("enabled", True)),
        calibration_buckets=tuple(
            Decimal(str(b)) for b in ((raw.get("calibration") or {}).get("buckets") or [])
        )
        or LearningPolicy.calibration_buckets,
    )
