#!/usr/bin/env python3
"""Clean up a workspace's uploaded documents, bank lines, matches, months, and runs (dev helper).

Preserves workspace profile, settings, members, and declared bank accounts.
Resets document and review item counters to 0.

Usage:
  uv run python -m scripts.clean_workspace --email owner@example.com
  uv run python -m scripts.clean_workspace --org org_01M4RHAWGCX18PH4987X992ZXA
"""

import argparse
import asyncio
import sys

import firebase_admin
from firebase_admin import auth
from google.cloud import firestore, storage

from app.core.settings import Settings

COLLECTIONS = (
    "documents",
    "bankLines",
    "invoices",
    "receipts",
    "ledgerEntries",
    "accountClassifications",
    "months",
    "matches",
    "reviewItems",
    "findings",
    "decisions",
    "runs",
    "events",
    "fileHashes",
)


async def clean_org_data(org_id: str, settings: Settings | None = None) -> dict[str, int | str]:
    settings = settings or Settings()
    db = firestore.Client(
        project=settings.google_cloud_project, database=settings.firestore_database
    )
    org_ref = db.collection("orgs").document(org_id)

    deleted_counts: dict[str, int | str] = {}
    for col_name in COLLECTIONS:
        col_ref = org_ref.collection(col_name)
        count = 0
        while True:
            docs = list(col_ref.limit(200).stream())
            if not docs:
                break
            batch = db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
            batch.commit()
        deleted_counts[col_name] = count

    # Reset counts on the root org doc
    org_doc = org_ref.get()
    if org_doc.exists:
        org_ref.update(
            {
                "counts": {
                    "documents": 0,
                    "openReviewItems": 0,
                    "openFindingsBySeverity": {},
                }
            }
        )

    # Clean storage bucket if configured
    try:
        storage_client = storage.Client(project=settings.google_cloud_project)
        bucket = storage_client.bucket(settings.docs_bucket)
        blobs = list(bucket.list_blobs(prefix=f"orgs/{org_id}/documents/"))
        if blobs:
            bucket.delete_blobs(blobs)
            deleted_counts["storageBlobs"] = len(blobs)
    except Exception as e:
        deleted_counts["storageWarning"] = str(e)

    return deleted_counts


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean up workspace documents and reconciliation runs."
    )
    parser.add_argument("--email", help="Workspace owner's email")
    parser.add_argument("--org", help="Workspace org ID")
    args = parser.parse_args()

    if not args.email and not args.org:
        print("Provide either --email or --org", file=sys.stderr)
        return 1

    settings = Settings()
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": settings.google_cloud_project})

    org_id = args.org
    if not org_id:
        user = auth.get_user_by_email(args.email)
        claims = user.custom_claims or {}
        org_id = claims.get("orgId")
        if not org_id:
            print(f"No workspace found for {args.email}", file=sys.stderr)
            return 1

    print(f"Cleaning workspace {org_id}...")
    counts = await clean_org_data(org_id, settings)
    print("Deleted items:")
    for k, v in counts.items():
        if v:
            print(f"  {k}: {v}")
    print("Workspace cleaned successfully. Members and bank accounts preserved.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
