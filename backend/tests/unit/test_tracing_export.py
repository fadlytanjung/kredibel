"""TRACE_EXPORT=cloud must start: its exporters are built at app start on Cloud Run (docs/17 §2).

A missing exporter package once stopped the worker from starting; nothing ran this path in tests.
"""

import google.auth
import pytest
from google.adk.telemetry.google_cloud import get_gcp_exporters
from google.auth.credentials import AnonymousCredentials


def test_the_cloud_trace_exporters_can_be_built(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        google.auth, "default", lambda *a, **k: (AnonymousCredentials(), "test-project")
    )
    hooks = get_gcp_exporters(enable_cloud_tracing=True)
    assert hooks.span_processors
