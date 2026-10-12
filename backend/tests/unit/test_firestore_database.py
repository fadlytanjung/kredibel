"""The services open Kredibel's own database (ADR-021); tests and the emulator keep (default)."""

from pathlib import Path

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.main import AppDeps

PLANS = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"


def test_the_client_uses_the_configured_database():
    deps = AppDeps(Settings(firestore_database="kredibel"), load_plans(PLANS))  # type: ignore[call-arg]
    assert deps.firestore._database == "kredibel"


def test_the_default_is_the_emulator_database():
    assert Settings().firestore_database == "(default)"
