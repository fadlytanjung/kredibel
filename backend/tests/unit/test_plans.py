"""Plan catalog parsing and validation (T013-01, AC-013-5)."""

import copy
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from app.adapters.policy_files import load_plans
from app.domain.plans import parse_plans

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"


@pytest.fixture
def raw() -> dict[str, Any]:
    return yaml.safe_load(PLANS_FILE.read_text())


def test_ac013_5_the_committed_catalog_loads():
    catalog = load_plans(PLANS_FILE)

    assert catalog.default_plan == "free_trial"
    assert [p.id for p in catalog.plans] == ["free_trial", "starter", "professional", "enterprise"]
    trial = catalog.plan("free_trial")
    assert trial.limits is not None
    assert trial.limits.extracted_pages_per_month == 400
    assert trial.limits.ai_spend_usd_per_month == Decimal("5.00")
    assert trial.trial_days == 30
    assert [lang.code for lang in catalog.languages if lang.status == "available"] == ["en"]


def test_ac013_5_unknown_key_is_rejected(raw):
    bad = copy.deepcopy(raw)
    bad["plans"][0]["limits"]["pagesPerMonth"] = 10

    with pytest.raises(ValidationError, match="pagesPerMonth"):
        parse_plans(bad)


def test_ac013_5_missing_default_plan_is_rejected(raw):
    bad = copy.deepcopy(raw)
    bad["defaultPlan"] = "gold"

    with pytest.raises(ValidationError, match="defaultPlan"):
        parse_plans(bad)


def test_ac013_5_default_plan_must_be_available(raw):
    bad = copy.deepcopy(raw)
    bad["defaultPlan"] = "starter"

    with pytest.raises(ValidationError, match="AVAILABLE"):
        parse_plans(bad)


def test_ac013_5_coming_soon_plan_with_limits_is_rejected(raw):
    bad = copy.deepcopy(raw)
    bad["plans"][1]["limits"] = copy.deepcopy(raw["plans"][0]["limits"])

    with pytest.raises(ValidationError, match="COMING_SOON"):
        parse_plans(bad)


def test_ac013_5_available_plan_needs_limits(raw):
    bad = copy.deepcopy(raw)
    del bad["plans"][0]["limits"]

    with pytest.raises(ValidationError, match="limits"):
        parse_plans(bad)


def test_ac013_5_money_limit_must_be_a_decimal_string_not_a_float(raw):
    bad = copy.deepcopy(raw)
    bad["plans"][0]["limits"]["aiSpendUsdPerMonth"] = 5.0

    with pytest.raises(ValidationError, match="decimal string"):
        parse_plans(bad)


def test_ac013_5_duplicate_plan_ids_are_rejected(raw):
    bad = copy.deepcopy(raw)
    bad["plans"].append(copy.deepcopy(raw["plans"][1]))

    with pytest.raises(ValidationError, match="duplicate"):
        parse_plans(bad)


def test_ac013_5_an_invalid_catalog_stops_start_up(tmp_path, raw):
    from app.core.settings import Settings
    from app.main import create_app

    bad = copy.deepcopy(raw)
    bad["defaultPlan"] = "starter"
    plans_file = tmp_path / "plans.yaml"
    plans_file.write_text(yaml.safe_dump(bad))

    with pytest.raises(ValidationError):
        create_app(Settings(plans_file=str(plans_file)))


def test_ac013_5_start_up_finds_the_catalog_from_the_backend_directory():
    from app.core.settings import Settings
    from app.main import create_app

    app = create_app(Settings())

    assert app.state.plans.default_plan == "free_trial"
