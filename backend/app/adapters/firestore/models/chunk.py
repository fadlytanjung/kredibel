"""orgs/{orgId}/chunks/{chunkId} as stored (docs/09 §3.21, spec 022)."""

from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class ChunkDoc(FirestoreModel):
    chunk_id: str
    doc_id: str
    doc_type: str
    page_no: int
    ordinal: int
    layout_id: str
    kind: str
    text: str
    box: dict[str, float] | None = None
    source: str
    months: list[str] = Field(default_factory=list)
    links: dict[str, Any] = Field(default_factory=dict)
