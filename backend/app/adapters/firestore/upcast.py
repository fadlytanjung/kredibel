"""Firestore document upcasting registry and chains.

Normative references: docs/specs/001-foundation/spec.md AC-001-19, docs/22 §3, ADR-013.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class SchemaTooNewError(Exception):
    """Raised when a document's schemaVersion is newer than the codebase knows."""

    def __init__(
        self,
        collection: str,
        doc_version: int,
        latest_version: int,
        doc_id: str | None = None,
    ) -> None:
        self.collection = collection
        self.doc_version = doc_version
        self.latest_version = latest_version
        self.doc_id = doc_id
        super().__init__(
            f"Document {doc_id or '<unidentified>'} in collection '{collection}' "
            f"has schemaVersion {doc_version}, newer than latest known version {latest_version}. "
            "Retry request on updated revision."
        )


_UPCASTERS: dict[tuple[str, int], Callable[[dict[str, Any]], dict[str, Any]]] = {}
_LATEST_VERSIONS: dict[str, int] = {}
_LOADED = False


def _ensure_loaded() -> None:
    global _LOADED
    if not _LOADED:
        _LOADED = True
        import app.adapters.firestore.upcasters  # noqa: F401


def register_collection_version(collection: str, latest_version: int) -> None:
    """Register the latest known schema version for a collection."""
    current = _LATEST_VERSIONS.get(collection, 1)
    if latest_version > current:
        _LATEST_VERSIONS[collection] = latest_version


def get_latest_version(collection: str) -> int:
    """Return the latest known schema version for a collection (default 1)."""
    _ensure_loaded()
    return _LATEST_VERSIONS.get(collection, 1)


def upcaster(collection: str, from_version: int) -> Callable[
    [Callable[[dict[str, Any]], dict[str, Any]]],
    Callable[[dict[str, Any]], dict[str, Any]],
]:
    """Decorator to register an upcaster step from from_version to from_version + 1."""

    def decorator(
        fn: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        _UPCASTERS[(collection, from_version)] = fn
        register_collection_version(collection, from_version + 1)
        return fn

    return decorator


def upcast(collection: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Upcast a document dictionary to the latest schema version for its collection."""
    latest = get_latest_version(collection)

    # Documents without schemaVersion are version 1
    current_version = doc.get("schemaVersion")
    if current_version is None:
        current_version = doc.get("schema_version", 1)

    if not isinstance(current_version, int):
        current_version = int(current_version)

    if current_version > latest:
        doc_id = doc.get("id")
        raise SchemaTooNewError(
            collection=collection,
            doc_version=current_version,
            latest_version=latest,
            doc_id=doc_id,
        )

    out = dict(doc)
    while current_version < latest:
        step_fn = _UPCASTERS.get((collection, current_version))
        if step_fn is None:
            raise KeyError(
                f"Missing upcaster for collection '{collection}' "
                f"from version {current_version} to {current_version + 1}"
            )
        out = step_fn(out)
        current_version += 1
        out["schemaVersion"] = current_version

    return out
