"""Upcasters for documents collection."""

from typing import Any

from app.adapters.firestore.upcast import upcaster


@upcaster("documents", from_version=1)
def documents_v1_to_v2(doc: dict[str, Any]) -> dict[str, Any]:
    """v1 kept duplicateOf/duplicateKind/duplicateDecision at the top level.

    v2 groups duplicate fields under `duplicate` object.
    """
    out = {
        k: v
        for k, v in doc.items()
        if k not in {"duplicateOf", "duplicateKind", "duplicateDecision"}
    }
    if doc.get("duplicateOf"):
        kind = doc.get("duplicateKind", "EXACT")
        code = (
            "D01_EXACT_FILE_DUPLICATE"
            if kind == "EXACT"
            else doc.get("duplicateCode", "D02_STATEMENT_PERIOD_DUPLICATE")
        )
        out["duplicate"] = {
            "ofDocId": doc["duplicateOf"],
            "kind": kind,
            "code": code,
            "decision": doc.get("duplicateDecision", "PENDING"),
        }
    out["schemaVersion"] = 2
    return out
