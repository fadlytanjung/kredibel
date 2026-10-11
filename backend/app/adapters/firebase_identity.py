"""IdentityAdmin on the Firebase Admin SDK (runs as kredibel-web with roles/firebaseauth.admin)."""

from typing import Any

import anyio
import firebase_admin
from firebase_admin import auth

from app.ports.identity_admin import IdentityAdmin, IdentityUser


def _ensure_app() -> None:
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()


class FirebaseIdentityAdmin(IdentityAdmin):
    """The Admin SDK is synchronous, so each call runs in a worker thread (docs/13 §2.3)."""

    def __init__(self) -> None:
        _ensure_app()

    async def set_claims(self, uid: str, claims: dict[str, str]) -> None:
        await anyio.to_thread.run_sync(auth.set_custom_user_claims, uid, claims)

    async def get_user(self, uid: str) -> IdentityUser:
        record: Any = await anyio.to_thread.run_sync(auth.get_user, uid)
        return IdentityUser(
            uid=record.uid,
            email=record.email,
            email_verified=bool(record.email_verified),
            display_name=record.display_name,
        )
