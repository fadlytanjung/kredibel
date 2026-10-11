"""Bank account numbers: normalize, mask, hash (docs/09 §3.4, §4; docs/14 §6). Pure."""

import hashlib
import re

MASK = "••••"


def account_digits(raw: str) -> str:
    """Digits only: "123-456 7890" and "1234567890" are the same account."""
    return re.sub(r"\D", "", raw)


def mask_account(digits: str) -> str:
    """The only readable form of an account number: ••••4821."""
    return f"{MASK}{digits[-4:]}"


def mask_tax_id(raw: str) -> str:
    """Tax IDs are stored masked; the profile shows the last 4 characters (docs/14 §6)."""
    compact = re.sub(r"\s", "", raw)
    return f"{MASK}{compact[-4:]}"


def account_hash(org_id: str, digits: str) -> str:
    """Keyed hash for matching without storing the number: sha256(orgId:digits) in the prototype.

    Production uses an HMAC with a Secret Manager key (docs/14 §6).
    """
    return hashlib.sha256(f"{org_id}:{digits}".encode()).hexdigest()


def normalize_bank_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().casefold()


def account_id_parts(org_id: str, bank_name: str, digits: str) -> tuple[str, str, str]:
    """Inputs of the deterministic bank account ID `acc_` + sha1(orgId|bank|digits) (docs/09 §4)."""
    return (org_id, normalize_bank_name(bank_name), digits)
