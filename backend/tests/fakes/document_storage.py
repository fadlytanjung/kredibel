"""In-memory fake document storage for tests."""

from app.ports.document_storage import DocumentStorage


class FakeDocumentStorage(DocumentStorage):
    def __init__(self) -> None:
        self.originals: dict[tuple[str, str, str], tuple[bytes, str]] = {}
        self.pages: dict[tuple[str, str, int, bool], bytes] = {}
        self.cache: dict[tuple[str, str], bytes] = {}

    async def store_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
        data: bytes,
        content_type: str,
    ) -> str:
        self.originals[(org_id, doc_id, extension)] = (data, content_type)
        return f"orgs/{org_id}/documents/{doc_id}/original{extension}"

    async def store_page(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        image_data: bytes,
        thumb_data: bytes,
    ) -> tuple[str, str]:
        self.pages[(org_id, doc_id, page_no, False)] = image_data
        self.pages[(org_id, doc_id, page_no, True)] = thumb_data
        return (
            f"orgs/{org_id}/documents/{doc_id}/pages/{page_no}.png",
            f"orgs/{org_id}/documents/{doc_id}/thumbs/{page_no}.png",
        )

    async def get_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
    ) -> bytes | None:
        entry = self.originals.get((org_id, doc_id, extension))
        return entry[0] if entry else None

    async def get_page_image(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        *,
        thumb: bool = False,
    ) -> bytes | None:
        return self.pages.get((org_id, doc_id, page_no, thumb))

    async def delete_prefix(self, org_id: str, doc_id: str) -> None:
        orig_keys = [k for k in self.originals if k[0] == org_id and k[1] == doc_id]
        for k in orig_keys:
            del self.originals[k]
        page_keys = [k for k in self.pages if k[0] == org_id and k[1] == doc_id]
        for k in page_keys:
            del self.pages[k]

    async def get_cached(self, org_id: str, key: str) -> bytes | None:
        return self.cache.get((org_id, key))

    async def put_cached(self, org_id: str, key: str, data: bytes) -> None:
        self.cache[(org_id, key)] = data
