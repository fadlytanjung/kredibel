"""Unit tests for Settings validation (T001-06)."""

import pytest
from pydantic import ValidationError


def test_t001_06_default_settings_valid():
    """Default settings instantiate without error."""
    from app.core.settings import Settings

    settings = Settings()
    assert settings.app_role in ("web", "worker", "all", "migrate")
    assert settings.google_cloud_project == "cloud-hack2skill"
    assert settings.region == "asia-southeast1"


def test_t001_06_invalid_app_role_fails():
    """Invalid APP_ROLE raises ValidationError."""
    from app.core.settings import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(app_role="invalid_role")  # type: ignore[arg-type]

    assert "app_role" in str(exc_info.value)


def test_t001_06_task_queue_mode_validation():
    """TASK_QUEUE_MODE must be 'cloud' or 'inline'."""
    from app.core.settings import Settings

    settings = Settings(task_queue_mode="inline")
    assert settings.task_queue_mode == "inline"

    with pytest.raises(ValidationError):
        Settings(task_queue_mode="invalid_mode")  # type: ignore[arg-type]


def test_t001_06_model_settings():
    """Models default to active Gemini models."""
    from app.core.settings import Settings

    settings = Settings()
    assert "gemini" in settings.model_fast
    assert "gemini" in settings.model_lite


def test_t001_06_content_capture_is_refused_on_real_data():
    """AI_CONTENT_CAPTURE=synthetic with DATA_CLASS=real stops start-up (docs/16 §6.1, ADR-017)."""
    from app.core.settings import Settings

    with pytest.raises(ValidationError, match="AI_CONTENT_CAPTURE"):
        Settings(ai_content_capture="synthetic", data_class="real")


def test_t001_06_span_content_capture_follows_ai_content_capture():
    """ADK span content is on only with synthetic capture, whatever the env var says."""
    from app.core.settings import Settings

    assert Settings(ai_content_capture="synthetic", data_class="synthetic").capture_span_content
    assert not Settings(ai_content_capture="off").capture_span_content
    assert not Settings(
        ai_content_capture="off", adk_capture_message_content_in_spans=True
    ).capture_span_content
