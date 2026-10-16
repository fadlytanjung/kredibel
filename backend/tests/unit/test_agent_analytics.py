"""Run history in BigQuery (spec 017, T017-03, AC-017-2…4): the plugin is attached only with the
feature on, never logs page images, drops content unless capture is synthetic, masks numbers in
what it keeps, and a plugin that cannot be built never fails a run. No GCP calls."""

from typing import Any

import pytest

from app.core.settings import Settings
from app.observability import agent_analytics
from app.observability.agent_analytics import agent_analytics_plugins, logger_options, mask_content


def settings(**kw: Any) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[call-arg]


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(agent_analytics, "_built", {})


def test_ac017_2_off_by_default_so_no_run_reaches_bigquery():
    assert agent_analytics_plugins(settings()) == []


def test_ac017_3_without_synthetic_capture_the_content_columns_are_dropped():
    options = logger_options(settings(ai_content_capture="off"))
    assert options["payload_column_denylist"] == ["content", "content_parts"]
    assert options["log_multi_modal_content"] is False and options["gcs_bucket_name"] is None
    assert options["table_id"] == "agent_events"
    synthetic = logger_options(settings(ai_content_capture="synthetic", data_class="synthetic"))
    assert synthetic["payload_column_denylist"] is None
    assert synthetic["gcs_bucket_name"] == "cloud-hack2skill-kredibel-agent-content"
    assert synthetic["log_multi_modal_content"] is False


def test_ac017_3_kept_content_has_account_and_id_numbers_masked():
    content = {
        "text": "to MERIDIAN SAVINGS 0081234567720 24,500,000.00",
        "parts": ["NPWP 99.731.204.5-018.000", 3],
    }
    assert mask_content(content, "LLM_REQUEST") == {
        "text": "to MERIDIAN SAVINGS ••••7720 24,500,000.00",
        "parts": ["NPWP ••••8000", 3],
    }


def test_ac017_2_on_attaches_one_plugin_on_the_analytics_dataset(monkeypatch):
    built: list[dict[str, Any]] = []

    class Plugin:
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)

    import google.adk.plugins.bigquery_agent_analytics_plugin as module

    monkeypatch.setattr(module, "BigQueryAgentAnalyticsPlugin", Plugin)
    on = settings(feature_agent_analytics=True)
    first, again = agent_analytics_plugins(on), agent_analytics_plugins(on)
    assert len(first) == 1 and first == again, "one plugin per process"
    [kwargs] = built
    assert (kwargs["project_id"], kwargs["dataset_id"], kwargs["location"]) == (
        "cloud-hack2skill",
        "kredibel_agent_analytics",
        "asia-southeast1",
    )
    assert kwargs["config"].log_multi_modal_content is False


def test_ac017_4_a_plugin_that_cannot_be_built_never_fails_a_run(monkeypatch):
    import google.adk.plugins.bigquery_agent_analytics_plugin as module

    def broken(**_: Any) -> Any:
        raise RuntimeError("no dataset")

    monkeypatch.setattr(module, "BigQueryAgentAnalyticsPlugin", broken)
    assert agent_analytics_plugins(settings(feature_agent_analytics=True)) == []
