"""Sample example migration (0000_example) for AC-001-20."""

from typing import Any

from migrations import Migration


def transform_example_item(doc: dict[str, Any]) -> dict[str, Any]:
    """Transform example items v1 to v2 by grouping sample fields."""
    out = dict(doc)
    out["migrated"] = True
    out["schemaVersion"] = 2
    return out


MIGRATION = Migration(
    id="0000_example",
    description="Sample example migration v1 -> v2 (AC-001-20)",
    kind="backfill",
    collection_group="example_items",
    from_version=1,
    to_version=2,
    transform=transform_example_item,
    requires_indexes=[],
)
