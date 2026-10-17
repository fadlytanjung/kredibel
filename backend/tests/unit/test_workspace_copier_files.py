"""A demo copy's files (spec 021, AC-021-2): every file under the template is copied to the new
workspace except the reading cache, which is most of the files and only saves a reading again."""

from typing import Any

from app.adapters.firestore.workspace_copier import FirestoreWorkspaceCopier


class _Blob:
    def __init__(self, name: str) -> None:
        self.name = name


class _Bucket:
    def __init__(self, names: list[str]) -> None:
        self.names = names
        self.copied: list[str] = []

    def list_blobs(self, prefix: str) -> list[_Blob]:
        return [_Blob(n) for n in self.names if n.startswith(prefix)]

    def copy_blob(self, blob: _Blob, bucket: Any, name: str) -> None:
        self.copied.append(name)


async def test_ac021_2_the_files_are_copied_but_not_the_reading_cache():
    bucket = _Bucket(
        [
            "orgs/org_t/documents/doc_1/original.pdf",
            "orgs/org_t/extractions/doc_1/p1.md",
            "orgs/org_t/cache/abc/flash-3-1f.json",
            "orgs/org_other/documents/doc_9/original.pdf",
        ]
    )
    copier = FirestoreWorkspaceCopier(db=None, project_id="p", bucket_name="b")  # type: ignore[arg-type]
    copier._bucket = bucket  # type: ignore[assignment]

    await copier._copy_files("org_t", "org_new")

    assert sorted(bucket.copied) == [
        "orgs/org_new/documents/doc_1/original.pdf",
        "orgs/org_new/extractions/doc_1/p1.md",
    ]
