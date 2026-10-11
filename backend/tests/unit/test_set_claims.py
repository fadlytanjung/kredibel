"""Unit tests for set_claims argument parsing (T001-13)."""


def test_t001_13_set_claims_module_importable():
    """set_claims script is importable and defines set_user_claims."""
    from scripts.set_claims import set_user_claims

    assert callable(set_user_claims)
