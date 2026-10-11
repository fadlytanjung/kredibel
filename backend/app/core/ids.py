"""Identifiers: prefixed ULIDs for new records, deterministic content IDs (docs/09 §1, §4)."""

import hashlib

from ulid import ULID


def new_id(prefix: str) -> str:
    """A sortable unique ID such as org_01J9Z3…; the prefix names the record type."""
    return f"{prefix}_{ULID()}"


def content_id(prefix: str, *parts: str) -> str:
    """docs/09 §4: prefix + 16 hex of sha1 of the parts joined by "|", so re-runs upsert."""
    digest = hashlib.sha1("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"{prefix}_{digest[:16]}"
