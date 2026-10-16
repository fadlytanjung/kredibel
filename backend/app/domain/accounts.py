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


def statement_account(bank_name: str | None, account_masked: str | None) -> str:
    """The account a statement belongs to (docs/09 §3.5): the bank's first line, spaces collapsed,
    and the masked number. A branch line the reader caught on some statements only
    ("…Bank\\nBandung Dago Branch") does not make a second account."""
    lines = (bank_name or "").strip().splitlines()
    bank = " ".join(lines[0].split()) if lines else ""
    return " ".join(x for x in (bank, (account_masked or "").strip()) if x)


_NUMBER_RUN = re.compile(r"\d[\d.\-]*\d|\d")
_GROUPED_RUN = re.compile(r"\b\d{4}(?: \d{4}){2,}\b")
_AMOUNT = re.compile(r"^\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?$|^\d+[.,]\d{1,2}$")
_DATE = re.compile(r"^\d{1,4}[./-]\d{1,2}(?:[./-]\d{1,4})?$")
MIN_ID_DIGITS = 8


def mask_numbers_in_text(text: str) -> str:
    """Account and ID numbers inside free text (a page's witness words, a description) masked to
    their last 4 digits; amounts and dates stay as printed (docs/14 §6, non-negotiable 13)."""

    def one(match: re.Match[str]) -> str:
        token = match.group(0)
        if _AMOUNT.match(token) or _DATE.match(token):
            return token
        digits = account_digits(token)
        return mask_account(digits) if len(digits) >= MIN_ID_DIGITS else token

    grouped = _GROUPED_RUN.sub(lambda m: mask_account(account_digits(m.group(0))), text)
    return _NUMBER_RUN.sub(one, grouped)
