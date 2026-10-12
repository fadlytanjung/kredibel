"""Cloud Run reads the mounted kredibel-env secret through ENV_FILE (ADR-024)."""

from app.core.settings import Settings


def test_settings_read_the_file_env_file_names(tmp_path, monkeypatch):
    mounted = tmp_path / ".env"
    mounted.write_text("FIRESTORE_DATABASE=kredibel\nDATA_CLASS=real\nMODEL_LITE=lite-from-secret\n")
    monkeypatch.setenv("ENV_FILE", str(mounted))
    for key in ("FIRESTORE_DATABASE", "DATA_CLASS", "MODEL_LITE"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert (settings.firestore_database, settings.data_class, settings.model_lite) == (
        "kredibel",
        "real",
        "lite-from-secret",
    )


def test_a_service_env_var_wins_over_the_shared_file(tmp_path, monkeypatch):
    mounted = tmp_path / ".env"
    mounted.write_text("APP_ROLE=all\nLOG_LEVEL=DEBUG\n")
    monkeypatch.setenv("ENV_FILE", str(mounted))
    monkeypatch.setenv("APP_ROLE", "worker")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert (settings.app_role, settings.log_level) == ("worker", "DEBUG")
