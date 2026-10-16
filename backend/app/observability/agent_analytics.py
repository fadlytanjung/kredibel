"""Run history in BigQuery (spec 017, T017-03, ADR-017; docs/17 §8).

The ADK BigQuery Agent Analytics plugin, attached to every workflow run when
FEATURE_AGENT_ANALYTICS is on (the dataset, bucket and IAM of docs/16 §4 step 11 must exist).
Content follows AI_CONTENT_CAPTURE: off drops it, synthetic keeps text with account and ID numbers
masked; page images are never logged. A plugin that cannot be built never fails a run: the run goes
on without it and `agent_events_dropped` is logged (a logs-based metric counts it).
"""

from typing import Any

import structlog

from app.core.settings import Settings
from app.domain.accounts import mask_numbers_in_text

_log = structlog.get_logger()
TABLE = "agent_events"
_built: dict[tuple[str, str, str, bool], list[Any]] = {}


def mask_content(content: Any, event_type: str = "") -> Any:
    """The plugin's content formatter: every string inside, masked; the shape kept."""
    if isinstance(content, str):
        return mask_numbers_in_text(content)
    if isinstance(content, dict):
        return {k: mask_content(v, event_type) for k, v in content.items()}
    if isinstance(content, list | tuple):
        return [mask_content(v, event_type) for v in content]
    return content


def logger_options(settings: Settings) -> dict[str, Any]:
    """BigQueryLoggerConfig arguments for this deployment (pure, so it is tested without GCP)."""
    capture = settings.ai_content_capture == "synthetic"
    return {
        "table_id": TABLE,
        "log_multi_modal_content": False,  # never page images
        "content_formatter": mask_content,
        "gcs_bucket_name": settings.agent_content_bucket if capture else None,
        "payload_column_denylist": None if capture else ["content", "content_parts"],
    }


def agent_analytics_plugins(settings: Settings) -> list[Any]:
    """The plugins a workflow run attaches: none while the feature is off. Built once per process,
    because the plugin keeps a write stream and a background queue."""
    if not settings.feature_agent_analytics:
        return []
    key = (
        settings.google_cloud_project,
        settings.analytics_dataset,
        settings.analytics_location,
        settings.ai_content_capture == "synthetic",
    )
    if key in _built:
        return _built[key]
    try:
        from google.adk.plugins.bigquery_agent_analytics_plugin import (  # noqa: PLC0415
            BigQueryAgentAnalyticsPlugin,
            BigQueryLoggerConfig,
        )

        plugin = BigQueryAgentAnalyticsPlugin(
            project_id=settings.google_cloud_project,
            dataset_id=settings.analytics_dataset,
            location=settings.analytics_location,
            config=BigQueryLoggerConfig(**logger_options(settings)),
        )
        plugins: list[Any] = [plugin]
    except Exception as exc:  # noqa: BLE001 - a run never fails for its analytics
        _log.warning("agent_events_dropped", reason=type(exc).__name__)
        plugins = []
    _built[key] = plugins
    return plugins
