"""Shared fixtures."""

import os
import socket

import pytest

_EMULATOR = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")


@pytest.fixture(autouse=True)
def _never_a_real_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every Firestore client at the emulator, so no test can reach a real project
    through the developer's credentials (docs/13 §5)."""
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", _EMULATOR)


@pytest.fixture
def firestore_emulator() -> str:
    """The emulator's host:port; skips the test when it is not running (docs/13 §5: optional).

    Start it with `make docker-up`.
    """
    name, _, port = _EMULATOR.partition(":")
    try:
        with socket.create_connection((name, int(port or 8080)), timeout=0.3):
            pass
    except OSError:
        pytest.skip(f"Firestore emulator not reachable at {_EMULATOR}")
    return _EMULATOR
