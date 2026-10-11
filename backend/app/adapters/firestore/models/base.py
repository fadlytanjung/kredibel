"""Base persistence model for Firestore documents."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class FirestoreModel(BaseModel):
    """Base model for versioned Firestore documents."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    SCHEMA_VERSION: ClassVar[int] = 1
    schema_version: int = Field(default=1, alias="schemaVersion")
