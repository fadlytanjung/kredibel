#!/usr/bin/env python3
"""Set custom claims {orgId, role} on a Firebase user and upsert org member record.

Normative reference: docs/specs/001-foundation/tasks.md T001-13 and docs/14 §3.
Usage:
  python -m scripts.set_claims --uid <UID> --org-id org_demo --role owner
"""

import argparse
import sys
from typing import Any

import firebase_admin
from firebase_admin import auth, firestore


def init_firebase() -> None:
    """Initialize Firebase Admin SDK if not already initialized."""
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()


def set_user_claims(
    uid: str,
    org_id: str,
    role: str = "owner",
    email: str | None = None,
) -> dict[str, Any]:
    """Set custom claims and upsert member document in Firestore."""
    init_firebase()

    claims = {"orgId": org_id, "role": role}
    auth.set_custom_user_claims(uid, claims)

    # Upsert member document under orgs/{orgId}/members/{uid}
    db = firestore.client()
    member_ref = db.collection("orgs").document(org_id).collection("members").document(uid)
    member_data: dict[str, Any] = {
        "uid": uid,
        "role": role,
        "orgId": org_id,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    if email:
        member_data["email"] = email

    member_ref.set(member_data, merge=True)

    return {
        "uid": uid,
        "claims": claims,
        "firestore_path": f"orgs/{org_id}/members/{uid}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set Firebase custom claims and org member record."
    )
    parser.add_argument("--uid", required=True, help="Firebase user UID")
    parser.add_argument(
        "--org-id", required=True, help="Organization / workspace ID (e.g. org_demo)"
    )
    parser.add_argument(
        "--role",
        default="owner",
        choices=["owner", "accountant", "reviewer", "viewer"],
    )
    parser.add_argument("--email", help="Optional user email")

    args = parser.parse_args()

    try:
        result = set_user_claims(
            uid=args.uid,
            org_id=args.org_id,
            role=args.role,
            email=args.email,
        )
        print("Claims successfully set:")
        print(f"  UID: {result['uid']}")
        print(f"  Claims: {result['claims']}")
        print(f"  Member doc: {result['firestore_path']}")
        return 0
    except Exception as exc:
        print(f"Error setting claims: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
