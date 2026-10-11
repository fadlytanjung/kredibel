"""Shared Firestore transaction helpers."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from google.api_core.exceptions import Aborted

_TXN_ATTEMPTS = 6


def dump(model: Any) -> dict[str, Any]:
    return model.model_dump(by_alias=True, exclude_none=True)


def _is_contention(exc: Exception) -> bool:
    # The SDK reports a lost race as Aborted, or as ValueError once its own attempts run out.
    return isinstance(exc, Aborted) or (
        type(exc) is ValueError and str(exc).startswith("Failed to commit transaction")
    )


async def with_backoff[T](attempt: Callable[[], Awaitable[T]]) -> T:
    """Run a single-attempt transaction until it commits, with jittered backoff.

    The SDK retries a conflicting transaction immediately, so two writers of the same hot
    documents (system/signup) can keep aborting each other. Random waits break the tie, and the
    loser re-reads and sees what the winner wrote.
    """
    for n in range(_TXN_ATTEMPTS):
        try:
            return await attempt()
        except Exception as exc:
            if not _is_contention(exc) or n == _TXN_ATTEMPTS - 1:
                raise
            await asyncio.sleep(random.uniform(0.05, 0.2) * (n + 1))
    raise AssertionError("unreachable")
