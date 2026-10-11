"""Firestore collection upcasters package."""

# Import all upcaster modules to ensure their @upcaster decorators execute
from app.adapters.firestore.upcasters import documents  # noqa: F401

__all__ = ["documents"]
