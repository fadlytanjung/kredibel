"""A demo workspace is a copy of the demo template workspace (spec 021, AC-021-1, AC-021-2). Pure.

The template's books were read, checked and reconciled once by the real workflows; a copy carries
every record and file, with the template's workspace ID and people swapped for the new workspace and
its owner, so IDs, links and storage paths keep pointing inside the copy.
"""

from typing import Any

# Not copied: who belongs to the template, its history, its conversations and its usage.
SKIPPED_COLLECTIONS = frozenset(
    {"members", "invites", "events", "assistantThreads", "usage", "usageMonthly"}
)
# The new workspace's record sets these itself; the rest of the template's record (counts, ledger
# mappings, learning) is merged in after it is created.
OWN_WORKSPACE_FIELDS = frozenset(
    {
        "orgId",
        "name",
        "entityType",
        "profile",
        "country",
        "timezone",
        "currency",
        "defaultLanguage",
        "subscription",
        "createdBy",
        "createdAt",
        "schemaVersion",
    }
)


def rewrite(value: Any, replace: dict[str, str]) -> Any:
    """Every string, at any depth and in keys too, with each `old` swapped for its `new`; other
    values (numbers, timestamps, vectors) unchanged."""
    if isinstance(value, str):
        for old, new in replace.items():
            if old and old in value:
                value = value.replace(old, new)
        return value
    if isinstance(value, dict):
        return {rewrite(k, replace): rewrite(v, replace) for k, v in value.items()}
    if isinstance(value, list):
        return [rewrite(v, replace) for v in value]
    if isinstance(value, tuple):
        return tuple(rewrite(v, replace) for v in value)
    return value


def workspace_extras(record: dict[str, Any], replace: dict[str, str]) -> dict[str, Any]:
    """The template record's fields the new workspace takes over, rewritten."""
    return {k: rewrite(v, replace) for k, v in record.items() if k not in OWN_WORKSPACE_FIELDS}
