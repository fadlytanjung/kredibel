"""Database migration scripts and runner for Firestore.

Normative references: docs/22-data-migrations.md and docs/specs/001-foundation/tasks.md T001-31.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Migration:
    """Definition of a forward-only Firestore data migration."""

    id: str
    description: str
    kind: str  # "backfill" | "cleanup" | "gcs" | "index-dependent"
    collection_group: str
    from_version: int
    to_version: int
    transform: Callable[[dict[str, Any]], dict[str, Any]]
    requires_indexes: list[str] = field(default_factory=list)


def discover_migrations() -> list[Migration]:
    """Discover all migration scripts in order of their numeric prefix."""
    migrations_dir = Path(__file__).resolve().parent
    discovered: list[Migration] = []

    for file_path in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py")):
        mod_name = f"migrations.{file_path.stem}"
        mod = importlib.import_module(mod_name)
        migration = getattr(mod, "MIGRATION", None)
        if isinstance(migration, Migration):
            discovered.append(migration)

    return discovered


__all__ = ["Migration", "discover_migrations"]
