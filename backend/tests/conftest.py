"""Shared fixtures."""

import os
import socket

import pytest

_EMULATOR = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")


@pytest.fixture(autouse=True)
def _never_a_real_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point every Firestore client at the emulator, so no test can reach a real project
    through the developer's credentials (docs/13 §5), and read no developer .env."""
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", _EMULATOR)
    monkeypatch.setenv("ENV_FILE", os.devnull)


@pytest.fixture(autouse=True)
def _never_a_real_model_or_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """An AppDeps a test did not give a reader or bank line store gets fakes, never Gemini through
    the developer's credentials or a Firestore the build machine does not run (docs/15 §2)."""
    from tests.fakes.bank_line_repository import FakeBankLineRepository
    from tests.fakes.counterparty_repository import FakeCounterpartyRepository
    from tests.fakes.decision_repository import FakeDecisionRepository
    from tests.fakes.document_reader import FakeDocumentReader
    from tests.fakes.finding_repository import FakeFindingRepository
    from tests.fakes.ledger_repository import FakeLedgerRepository
    from tests.fakes.match_repository import FakeMatchRepository
    from tests.fakes.record_repository import fake_invoices, fake_receipts
    from tests.fakes.review_item_repository import FakeReviewItemRepository
    from tests.fakes.suggestion_repository import FakeSuggestionRepository

    monkeypatch.setattr("app.main.GeminiDocumentReader", lambda settings: FakeDocumentReader())
    monkeypatch.setattr("app.main.FirestoreBankLineRepository", lambda db: FakeBankLineRepository())
    monkeypatch.setattr("app.main.firestore_invoices", lambda db: fake_invoices())
    monkeypatch.setattr("app.main.firestore_receipts", lambda db: fake_receipts())
    monkeypatch.setattr("app.main.FirestoreFindingRepository", lambda db: FakeFindingRepository())
    monkeypatch.setattr("app.main.FirestoreDecisionRepository", lambda db: FakeDecisionRepository())
    monkeypatch.setattr("app.main.FirestoreMatchRepository", lambda db: FakeMatchRepository())
    monkeypatch.setattr("app.main.FirestoreReviewItemRepo", lambda db: FakeReviewItemRepository())
    monkeypatch.setattr("app.main.FirestoreLedgerRepository", lambda db: FakeLedgerRepository())
    monkeypatch.setattr(
        "app.main.FirestoreCounterpartyRepository", lambda db: FakeCounterpartyRepository()
    )
    monkeypatch.setattr(
        "app.main.FirestoreSuggestionRepository", lambda db: FakeSuggestionRepository()
    )


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
