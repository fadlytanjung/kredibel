"""Tests for Firestore model upcasting and schema versions (AC-001-19)."""

import json
from pathlib import Path

import pytest

from app.adapters.firestore.models.document import DocumentDocV2
from app.adapters.firestore.upcast import SchemaTooNewError, get_latest_version, upcast


def test_ac001_19_v1_fixture_upcasts_to_v2():
    """A stored v1 fixture of documents reads as the latest version (v2)."""
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "firestore" / "documents" / "v1.json"
    )
    v1_raw = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Assert raw fixture has v1 structure
    assert "duplicateOf" in v1_raw
    assert "duplicate" not in v1_raw

    # Upcast
    v2_raw = upcast("documents", v1_raw)
    assert v2_raw["schemaVersion"] == 2
    assert "duplicateOf" not in v2_raw
    assert "duplicate" in v2_raw
    assert v2_raw["duplicate"]["ofDocId"] == "doc_01HVOLD001"
    assert v2_raw["duplicate"]["kind"] == "EXACT"
    assert v2_raw["duplicate"]["code"] == "D01_EXACT_FILE_DUPLICATE"
    assert v2_raw["duplicate"]["decision"] == "PENDING"

    # Validate against target persistence model
    doc = DocumentDocV2.model_validate(v2_raw)
    assert doc.schema_version == 2
    assert doc.duplicate is not None
    assert doc.duplicate.of_doc_id == "doc_01HVOLD001"


def test_ac001_19_missing_schema_version_treated_as_v1():
    """A document with no schemaVersion is treated as version 1."""
    doc = {
        "id": "doc_no_version",
        "orgId": "org_demo",
        "docType": "SALES_INVOICE",
        "status": "UPLOADED",
    }
    upcast_doc = upcast("documents", doc)
    assert upcast_doc["schemaVersion"] == 2


def test_ac001_19_latest_version_passes_unchanged():
    """A document already at the latest version is returned unchanged."""
    latest_ver = get_latest_version("documents")
    doc = {
        "id": "doc_latest",
        "orgId": "org_demo",
        "docType": "PURCHASE_INVOICE",
        "status": "UPLOADED",
        "schemaVersion": latest_ver,
    }
    upcast_doc = upcast("documents", doc)
    assert upcast_doc["schemaVersion"] == latest_ver
    assert upcast_doc["id"] == "doc_latest"


def test_ac001_19_schema_too_new_raises_error():
    """A document newer than the latest known version raises SchemaTooNewError."""
    doc = {
        "id": "doc_future",
        "schemaVersion": 999,
    }
    with pytest.raises(SchemaTooNewError) as exc_info:
        upcast("documents", doc)

    assert exc_info.value.collection == "documents"
    assert exc_info.value.doc_version == 999
    assert exc_info.value.latest_version == get_latest_version("documents")
