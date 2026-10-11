"""Firebase IdentityAdmin adapter (T013-05)."""

from types import SimpleNamespace

from app.adapters import firebase_identity
from app.adapters.firebase_identity import FirebaseIdentityAdmin


async def test_t013_05_set_claims_and_get_user_go_through_the_admin_sdk(monkeypatch):
    calls: list[tuple[str, dict[str, str]]] = []
    monkeypatch.setattr(firebase_identity, "_ensure_app", lambda: None)
    monkeypatch.setattr(
        firebase_identity.auth, "set_custom_user_claims", lambda uid, c: calls.append((uid, c))
    )
    monkeypatch.setattr(
        firebase_identity.auth,
        "get_user",
        lambda uid: SimpleNamespace(
            uid=uid, email="owner@example.test", email_verified=True, display_name="Owner"
        ),
    )
    admin = FirebaseIdentityAdmin()

    await admin.set_claims("u-1", {"orgId": "org_x", "role": "owner"})
    user = await admin.get_user("u-1")

    assert calls == [("u-1", {"orgId": "org_x", "role": "owner"})]
    assert (user.email, user.email_verified) == ("owner@example.test", True)
