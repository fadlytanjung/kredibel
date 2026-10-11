"""Unit tests for Settings validation (T001-06)."""

import pytest
from pydantic import ValidationError


def test_t001_06_default_settings_valid():
    """Default settings instantiate without error."""
    from app.core.settings import Settings

    settings = Settings()
    assert settings.app_role in ("web", "worker", "all")
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
