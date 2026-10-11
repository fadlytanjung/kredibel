"""Document cloud storage port interface (docs/09 §7, spec 003 plan).

Handles storing original uploads, rendered 150 dpi page images, and 300 px thumbnails.
"""

from typing import Protocol


class DocumentStorage(Protocol):
    async def store_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Store the original document bytes at orgs/{orgId}/documents/{docId}/original.{ext}."""
        ...

    async def store_page(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        image_data: bytes,
        thumb_data: bytes,
    ) -> tuple[str, str]:
        """Store the 150 dpi page image and 300 px thumbnail. Returns (image_path, thumb_path)."""
        ...

    async def get_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
    ) -> bytes | None:
        """Fetch the original document bytes."""
        ...

    async def get_page_image(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        *,
        thumb: bool = False,
    ) -> bytes | None:
        """Fetch rendered page PNG or thumbnail."""
        ...

    async def delete_prefix(self, org_id: str, doc_id: str) -> None:
        """Delete all objects under orgs/{orgId}/documents/{docId}/."""
        ...
