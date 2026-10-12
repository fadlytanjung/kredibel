"""E01, E02, E05: how well the document could be read, and whose it is (docs/08 §2.1)."""

from decimal import Decimal

from app.domain.findings import Evidence, Finding
from app.domain.invoice_records import is_own_name
from app.domain.models.document import DocType

from .base import CheckContext, check

_READ = {DocType.BANK_STATEMENT, DocType.SALES_INVOICE, DocType.PURCHASE_INVOICE, DocType.RECEIPT}


@check("E01_LOW_EXTRACTION_AGREEMENT")
def low_agreement(ctx: CheckContext) -> list[Finding]:
    reading = ctx.doc.reading or {}
    if reading.get("agreement") is None:
        return []
    agreement = Decimal(str(reading["agreement"]))
    if agreement >= ctx.policy.extraction.min_agreement:
        return []
    return [
        ctx.finding(
            "E01_LOW_EXTRACTION_AGREEMENT",
            "reading",
            category="EXTRACTION",
            severity="MEDIUM",
            title="Part of this document could not be confirmed against its text",
            facts={
                "agreement": f"{agreement:.3f}",
                "fieldsAgreed": str(reading.get("fieldsAgreed", "")),
                "fieldsCompared": str(reading.get("fieldsCompared", "")),
            },
            evidence=[Evidence(doc_id=ctx.doc_id)],
        )
    ]


@check("E02_EXTRACTION_FAILED")
def nothing_read(ctx: CheckContext) -> list[Finding]:
    if ctx.doc.doc_type not in _READ or ctx.doc.reading is None:
        return []
    if ctx.doc.reading.get("lines"):
        return []
    return [
        ctx.finding(
            "E02_EXTRACTION_FAILED",
            "reading",
            category="EXTRACTION",
            severity="HIGH",
            title="Nothing usable could be read from this document",
            facts={"pages": str(ctx.doc.page_count or 0)},
            evidence=[Evidence(doc_id=ctx.doc_id)],
        )
    ]


@check("E05_PARTY_UNCLEAR")
def party_unclear(ctx: CheckContext) -> list[Finding]:
    if not ctx.own_names:
        return []
    out: list[Finding] = []
    for inv in ctx.invoices:
        if is_own_name(inv.issuer_name, ctx.own_names) or is_own_name(
            inv.buyer_name, ctx.own_names
        ):
            continue
        c = inv.consensus.get("buyerName") or inv.consensus.get("issuerName") or {}
        out.append(
            ctx.finding(
                "E05_PARTY_UNCLEAR",
                inv.invoice_id,
                category="EXTRACTION",
                severity="LOW",
                title="Neither the issuer nor the buyer is this business",
                facts={"issuer": inv.issuer_name or "", "buyer": inv.buyer_name or ""},
                evidence=[
                    Evidence(
                        doc_id=ctx.doc_id,
                        page=c.get("page"),
                        bbox=c.get("bbox"),
                        invoice_id=inv.invoice_id,
                        label="Parties",
                    )
                ],
                month=inv.month,
            )
        )
    return out
