"""Tests for tools/checks/schema_drift.py (AC-001-21)."""

import json
import tempfile
from pathlib import Path

from tools.checks.schema_drift import inspect_models


def test_ac001_21_models_inspected_correctly():
    """inspect_models correctly extracts class name, schemaVersion, and fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "class SampleDoc:\n"
            "    SCHEMA_VERSION: int = 3\n"
            "    id: str\n"
            "    amount: int\n"
        )

        schema = inspect_models(tmp_path)
        assert "SampleDoc" in schema
        assert schema["SampleDoc"]["schemaVersion"] == 3
        assert schema["SampleDoc"]["fields"] == {"amount": "int", "id": "str"}


def test_ac001_21_schema_drift_detected():
    """Altered model fields or types detect schema drift against saved snapshot."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        py_file = tmp_path / "sample.py"
        py_file.write_text(
            "class SampleDoc:\n"
            "    SCHEMA_VERSION: int = 1\n"
            "    id: str\n"
            "    new_field: str\n"
        )

        old_snapshot = {
            "SampleDoc": {
                "file": "sample.py",
                "schemaVersion": 1,
                "fields": {"id": "str"},
            }
        }

        current_schema = inspect_models(tmp_path)
        current_json = json.dumps(current_schema, sort_keys=True)
        old_json = json.dumps(old_snapshot, sort_keys=True)

        assert current_json != old_json
