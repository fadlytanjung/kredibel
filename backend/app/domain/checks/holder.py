"""X05, X06: is this statement the workspace's own account (docs/08 §2.6, per statement)."""

from rapidfuzz import fuzz

from app.domain.findings import Evidence, Finding
from app.domain.models.document import DocType

from .base import CheckContext, check


def _fold(text: str) -> str:
    return " ".join(text.upper().split())


@check("X05_ACCOUNT_HOLDER_MISMATCH")
def holder_mismatch(ctx: CheckContext) -> list[Finding]:
    meta = ctx.doc.statement_meta or {}
    holder = meta.get("accountHolder")
    names = [n for n in ctx.own_names + [a.holder_name for a in ctx.accounts] if n]
    if ctx.doc.doc_type != DocType.BANK_STATEMENT or not holder or not names:
        return []
    best = max(fuzz.token_set_ratio(_fold(holder), _fold(n)) for n in names)
    if best >= ctx.policy.cross_document.holder_name_min_score:
        return []
    return [
        ctx.finding(
            "X05_ACCOUNT_HOLDER_MISMATCH",
            "holder",
            category="CROSS_DOCUMENT",
            severity="HIGH",
            title="The account holder is not this business or its owner",
            facts={"holder": holder, "bestMatch": f"{best:.0f}"},
            evidence=[Evidence(doc_id=ctx.doc_id, page=1, label="Account holder")],
        )
    ]


@check("X06_UNDECLARED_ACCOUNT")
def undeclared_account(ctx: CheckContext) -> list[Finding]:
    meta = ctx.doc.statement_meta or {}
    masked = meta.get("accountMasked")
    if ctx.doc.doc_type != DocType.BANK_STATEMENT or not masked:
        return []
    if any(a.account_masked[-4:] == masked[-4:] for a in ctx.accounts):
        return []
    return [
        ctx.finding(
            "X06_UNDECLARED_ACCOUNT",
            masked,
            category="CROSS_DOCUMENT",
            severity="LOW",
            title="This account is not among the workspace's bank accounts yet",
            facts={"bank": meta.get("bankName") or "", "account": masked},
            evidence=[Evidence(doc_id=ctx.doc_id, page=1, label="Account")],
        )
    ]
