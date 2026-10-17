"""Copy a workspace in Firestore and Cloud Storage (spec 021, AC-021-1, AC-021-2).

Streams every collection directly under `orgs/{source}` and `orgPrivate/{source}` (nested
collections are not copied: only assistant messages exist, and threads are skipped), rewrites each
record and writes it in batches; copies every object under `orgs/{source}/` in the documents bucket
with server-side copies. Nothing under the source is ever written.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from google.cloud.firestore import AsyncClient
from requests.adapters import HTTPAdapter

from app.domain.demo import SKIPPED_COLLECTIONS, rewrite, workspace_extras

BATCH = 400
PARALLEL_COPIES = 64
PARALLEL_COMMITS = 8  # batches of one collection written at the same time
# The reading cache is not copied: a copy reads again only if asked, and it is most of the files.
SKIPPED_FILE_FOLDERS = ("cache/",)


class FirestoreWorkspaceCopier:
    def __init__(self, db: AsyncClient, project_id: str, bucket_name: str) -> None:
        self._db = db
        self._project_id = project_id
        self._bucket_name = bucket_name
        self._bucket: storage.Bucket | None = None
        # Its own threads: the default pool has about five on one vCPU, and a demo copy moves
        # about two thousand files within a request's time.
        self._pool = ThreadPoolExecutor(max_workers=PARALLEL_COPIES, thread_name_prefix="copier")

    def _get_bucket(self) -> storage.Bucket:
        if self._bucket is None:
            credentials, _ = google.auth.default(  # pyright: ignore[reportUnknownMemberType]
                scopes=["https://www.googleapis.com/auth/devstorage.read_write"]
            )
            session = AuthorizedSession(credentials)
            adapter = HTTPAdapter(pool_connections=PARALLEL_COPIES, pool_maxsize=PARALLEL_COPIES)
            session.mount("https://", adapter)
            client = storage.Client(
                project=self._project_id, credentials=credentials, _http=session
            )
            self._bucket = client.bucket(self._bucket_name)
        return self._bucket

    async def _in_pool(self, work: Callable[..., Any], *args: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(self._pool, work, *args)

    @staticmethod
    async def _commit_all(batches: list[Any]) -> None:
        gate = asyncio.Semaphore(PARALLEL_COMMITS)

        async def commit(batch: Any) -> None:
            async with gate:
                await batch.commit()

        await asyncio.gather(*(commit(b) for b in batches))

    async def copy_records(self, source_org: str, target_org: str, replace: dict[str, str]) -> int:
        """Collections and files are copied side by side: the request has a time limit."""
        jobs = []
        for root in ("orgs", "orgPrivate"):
            source = self._db.collection(root).document(source_org)
            target = self._db.collection(root).document(target_org)
            async for collection in source.collections():
                if collection.id in SKIPPED_COLLECTIONS:
                    continue
                jobs.append(
                    self._copy_collection(collection, target.collection(collection.id), replace)
                )
        files = asyncio.create_task(self._copy_files(source_org, target_org))
        written: list[int] = await asyncio.gather(*jobs)
        await files
        return sum(written)

    async def _copy_collection(self, source: Any, target: Any, replace: dict[str, str]) -> int:
        batches: list[Any] = []
        written = 0
        async for snap in source.stream():
            if written % BATCH == 0:
                batches.append(self._db.batch())
            data = snap.to_dict() or {}
            batches[-1].set(target.document(rewrite(snap.id, replace)), rewrite(data, replace))
            written += 1
        await self._commit_all(batches)
        return written

    async def _copy_files(self, source_org: str, target_org: str) -> None:
        bucket = self._get_bucket()
        prefix = f"orgs/{source_org}/"
        listed = await self._in_pool(lambda: list(bucket.list_blobs(prefix=prefix)))
        blobs = [
            b for b in listed if not str(b.name)[len(prefix) :].startswith(SKIPPED_FILE_FOLDERS)
        ]
        gate = asyncio.Semaphore(PARALLEL_COPIES)

        async def copy(blob: storage.Blob) -> None:
            name = f"orgs/{target_org}/{str(blob.name)[len(prefix) :]}"
            async with gate:
                await self._in_pool(bucket.copy_blob, blob, bucket, name)

        await asyncio.gather(*(copy(b) for b in blobs))

    async def copy_workspace_fields(
        self, source_org: str, target_org: str, replace: dict[str, str]
    ) -> None:
        record = (await self._db.collection("orgs").document(source_org).get()).to_dict() or {}
        extras = workspace_extras(record, replace)
        if extras:
            await self._db.collection("orgs").document(target_org).set(extras, merge=True)

    async def discard(self, org_id: str) -> None:
        async def clear(collection: Any) -> None:
            batches: list[Any] = []
            pending = 0
            async for snap in collection.stream():
                if pending % BATCH == 0:
                    batches.append(self._db.batch())
                batches[-1].delete(snap.reference)
                pending += 1
            await self._commit_all(batches)

        for root in ("orgs", "orgPrivate"):
            ref = self._db.collection(root).document(org_id)
            await asyncio.gather(*[clear(c) async for c in ref.collections()])
            await ref.delete()
        bucket = self._get_bucket()
        blobs = await self._in_pool(lambda: list(bucket.list_blobs(prefix=f"orgs/{org_id}/")))
        gate = asyncio.Semaphore(PARALLEL_COPIES)

        async def remove(blob: storage.Blob) -> None:
            async with gate:
                await self._in_pool(blob.delete)

        await asyncio.gather(*(remove(b) for b in blobs))
