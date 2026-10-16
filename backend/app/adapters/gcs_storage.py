"""Cloud Storage adapter for documents, pages, and thumbnails (docs/09 §7).

Normative references: docs/09 §7, docs/10 §2.2, ADR-011.
"""

from google.cloud import storage

from app.ports.document_storage import DocumentStorage


class GcsDocumentStorage(DocumentStorage):
    def __init__(self, project_id: str, bucket_name: str) -> None:
        self._project_id = project_id
        self._bucket_name = bucket_name
        self._client: storage.Client | None = None

    def _get_bucket(self) -> storage.Bucket:
        if self._client is None:
            self._client = storage.Client(project=self._project_id)
        return self._client.bucket(self._bucket_name)

    async def store_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
        data: bytes,
        content_type: str,
    ) -> str:
        blob_path = f"orgs/{org_id}/documents/{doc_id}/original{extension}"
        bucket = self._get_bucket()
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self._bucket_name}/{blob_path}"

    async def store_page(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        image_data: bytes,
        thumb_data: bytes,
    ) -> tuple[str, str]:
        bucket = self._get_bucket()
        image_path = f"orgs/{org_id}/documents/{doc_id}/pages/page-{page_no}.png"
        thumb_path = f"orgs/{org_id}/documents/{doc_id}/pages/page-{page_no}-thumb.png"

        b_img = bucket.blob(image_path)
        b_img.upload_from_string(image_data, content_type="image/png")

        b_thumb = bucket.blob(thumb_path)
        b_thumb.upload_from_string(thumb_data, content_type="image/png")

        return f"gs://{self._bucket_name}/{image_path}", f"gs://{self._bucket_name}/{thumb_path}"

    async def get_original(
        self,
        org_id: str,
        doc_id: str,
        extension: str,
    ) -> bytes | None:
        blob_path = f"orgs/{org_id}/documents/{doc_id}/original{extension}"
        bucket = self._get_bucket()
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    async def get_page_image(
        self,
        org_id: str,
        doc_id: str,
        page_no: int,
        *,
        thumb: bool = False,
    ) -> bytes | None:
        suffix = "-thumb.png" if thumb else ".png"
        blob_path = f"orgs/{org_id}/documents/{doc_id}/pages/page-{page_no}{suffix}"
        bucket = self._get_bucket()
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    async def delete_prefix(self, org_id: str, doc_id: str) -> None:
        bucket = self._get_bucket()
        for prefix in (
            f"orgs/{org_id}/documents/{doc_id}/",
            f"orgs/{org_id}/extractions/{doc_id}/",
        ):
            blobs = list(bucket.list_blobs(prefix=prefix))
            if blobs:
                bucket.delete_blobs(blobs)

    async def put_extraction(self, org_id: str, doc_id: str, page_no: int, markdown: str) -> None:
        blob = self._get_bucket().blob(f"orgs/{org_id}/extractions/{doc_id}/p{page_no}.md")
        blob.upload_from_string(
            markdown.encode("utf-8"), content_type="text/markdown; charset=utf-8"
        )

    async def get_extraction(self, org_id: str, doc_id: str, page_no: int) -> str | None:
        blob = self._get_bucket().blob(f"orgs/{org_id}/extractions/{doc_id}/p{page_no}.md")
        if not blob.exists():
            return None
        return blob.download_as_bytes().decode("utf-8")

    async def get_cached(self, org_id: str, key: str) -> bytes | None:
        blob = self._get_bucket().blob(f"orgs/{org_id}/cache/extraction/{key}")
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    async def put_cached(self, org_id: str, key: str, data: bytes) -> None:
        blob = self._get_bucket().blob(f"orgs/{org_id}/cache/extraction/{key}")
        blob.upload_from_string(data, content_type="application/json")
