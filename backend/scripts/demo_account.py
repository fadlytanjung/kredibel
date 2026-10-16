#!/usr/bin/env python3
"""Create or reset the public demo account (spec 024, AC-024-3): an email-and-password sign-in whose
workspace is a fresh copy of the demo company. Run it again to reset the demo's data.

Usage (from backend/):
  DEMO_ACCOUNT_EMAIL=demo@kredibel.app DEMO_ACCOUNT_PASSWORD=... \\
    uv run python -m scripts.demo_account
Prints the account's uid and new workspace ID only.
"""

import asyncio
import os
import sys


async def _run(email: str, password: str) -> int:
    import firebase_admin
    from firebase_admin import auth

    from app.adapters.policy_files import load_plans
    from app.core.auth import Principal
    from app.core.settings import Settings
    from app.main import AppDeps

    settings = Settings(demo_account_email=email)
    if not settings.demo_template_org:
        print("DEMO_TEMPLATE_ORG is not set: there is no demo company to copy.", file=sys.stderr)
        return 1
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": settings.google_cloud_project})
    try:
        user = auth.get_user_by_email(email)
        auth.update_user(user.uid, password=password, email_verified=True)
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=email, password=password, email_verified=True, display_name="Demo"
        )
    org = (user.custom_claims or {}).get("orgId")
    deps = AppDeps(settings, load_plans(settings.contract_path(settings.plans_file)))
    principal = Principal(uid=user.uid, email=email, org_id=org, role="owner" if org else None)
    workspace = await deps.workspace_service.reset_demo_account(principal)
    print(f"demo account {user.uid}: workspace {workspace.org_id} (a copy of the demo company)")
    return 0


def main() -> int:
    email = os.environ.get("DEMO_ACCOUNT_EMAIL", "").strip()
    password = os.environ.get("DEMO_ACCOUNT_PASSWORD", "")
    if not email or len(password) < 8:
        print(
            "Set DEMO_ACCOUNT_EMAIL and DEMO_ACCOUNT_PASSWORD (8 characters or more).",
            file=sys.stderr,
        )
        return 2
    return asyncio.run(_run(email, password))


if __name__ == "__main__":
    sys.exit(main())
