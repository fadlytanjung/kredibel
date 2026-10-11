"""Document persistence models (v1 and v2) for versioned storage.

Normative references: docs/22 §3 and docs/specs/001-foundation/tasks.md T001-30.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.adapters.firestore.models.base import FirestoreModel


class DuplicateDoc(BaseModel):
    """v2 grouped duplicate details."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    of_doc_id: str
    kind: str
    code: str
    decision: str = "PENDING"


class DocumentDocV2(FirestoreModel):
    """Document persistence model version 2."""

    SCHEMA_VERSION: ClassVar[int] = 2
    schema_version: int = Field(default=2, alias="schemaVersion")

    id: str
    org_id: str
    doc_type: str
    status: str
    duplicate: DuplicateDoc | None = None
    held_as_duplicate: bool = False
    file_name: str | None = None
    sha256: str | None = None
