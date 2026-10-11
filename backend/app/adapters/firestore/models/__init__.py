"""Persistence models package."""

from app.adapters.firestore.models.base import FirestoreModel
from app.adapters.firestore.models.document import DocumentDocV2, DuplicateDoc

__all__ = ["FirestoreModel", "DocumentDocV2", "DuplicateDoc"]
