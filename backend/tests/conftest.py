"""Shared fixtures."""

import os
import socket

import pytest


@pytest.fixture
def firestore_emulator() -> str:
    """The emulator's host:port; skips the test when it is not running (docs/13 §5: optional).

    Start it with `make docker-up`.
    """
    host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    name, _, port = host.partition(":")
    try:
        with socket.create_connection((name, int(port or 8080)), timeout=0.3):
            pass
    except OSError:
        pytest.skip(f"Firestore emulator not reachable at {host}")
    os.environ["FIRESTORE_EMULATOR_HOST"] = host
    return host
