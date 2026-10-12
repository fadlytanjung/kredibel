"""M01–M04, M06: what the PDF file itself says about its history (docs/08 §2.4). Weak signals alone;
they matter together and next to the arithmetic."""

import re
from collections import Counter, defaultdict

from app.domain.findings import Evidence, Finding
from app.domain.page_triage import TextLayerStatus

from .base import CheckContext, ValueFont, check

_SUBSET = re.compile(r"^[A-Z]{6}\+")  # embedded font subsets get a random prefix per file


@check("M01_EDITING_SOFTWARE_PRODUCER")
def editing_software(ctx: CheckContext) -> list[Finding]:
    pdf = ctx.pdf
    if pdf is None:
        return []
    tools = " / ".join(t for t in (pdf.producer, pdf.creator) if t)
    if not tools or not any(p.search(tools) for p in ctx.policy.editor_patterns()):
        return []
    return [
        ctx.finding(
            "M01_EDITING_SOFTWARE_PRODUCER",
            "producer",
            category="STRUCTURE",
            severity="MEDIUM",
            title="The file was last saved by a general-purpose editing tool",
            facts={"producer": pdf.producer or "", "creator": pdf.creator or ""},
            evidence=[Evidence(doc_id=ctx.doc_id, label="File properties")],
        )
    ]


@check("M02_MODIFIED_AFTER_CREATION")
def modified_after_creation(ctx: CheckContext) -> list[Finding]:
    pdf = ctx.pdf
    if pdf is None or pdf.created is None or pdf.modified is None:
        return []
    minutes = (pdf.modified - pdf.created).total_seconds() / 60
    if minutes <= ctx.policy.structure.modified_after_creation_minutes:
        return []
    return [
        ctx.finding(
            "M02_MODIFIED_AFTER_CREATION",
            "dates",
            category="STRUCTURE",
            severity="MEDIUM",
            title="The file was changed after it was created",
            facts={
                "created": pdf.created.isoformat(),
                "modified": pdf.modified.isoformat(),
                "minutesLater": f"{minutes:.0f}",
            },
            evidence=[Evidence(doc_id=ctx.doc_id, label="File properties")],
        )
    ]


@check("M03_MULTIPLE_REVISIONS")
def multiple_revisions(ctx: CheckContext) -> list[Finding]:
    pdf = ctx.pdf
    if pdf is None or pdf.revisions <= 1:
        return []
    content = "CONTENT" in pdf.revision_changes
    return [
        ctx.finding(
            "M03_MULTIPLE_REVISIONS",
            "revisions",
            category="STRUCTURE",
            severity="HIGH" if content else "MEDIUM",
            title="The file was saved again after it was issued"
            + (", and page content was replaced" if content else ""),
            facts={"revisions": str(pdf.revisions), "changes": ", ".join(pdf.revision_changes)},
            evidence=[Evidence(doc_id=ctx.doc_id, label="File history")],
        )
    ]


def _font(v: ValueFont) -> str:
    return f"{_SUBSET.sub('', v.font)} {v.size:.1f}"


def _boxes(ctx: CheckContext) -> dict[int, list[dict[str, float]]]:
    """Where the read transaction values sit: M04 looks only at those, not at bold totals."""
    out: dict[int, list[dict[str, float]]] = defaultdict(list)
    for line in ctx.lines:
        for field in ("amount", "balance"):
            c = line.consensus.get(field, {})
            if c.get("bbox") and c.get("page"):
                out[int(c["page"])].append(c["bbox"])
    for inv in ctx.invoices:
        for key, c in inv.consensus.items():
            if key.startswith("lines.") and key.endswith(".amount") and c.get("bbox"):
                out[int(c["page"])].append(c["bbox"])
    return out


def _inside(v: ValueFont, boxes: list[dict[str, float]]) -> bool:
    cx, cy = (v.x0 + v.x1) / 2, (v.top + v.bottom) / 2
    return any(
        b["x0"] - 0.002 <= cx <= b["x1"] + 0.002 and b["y0"] - 0.002 <= cy <= b["y1"] + 0.002
        for b in boxes
    )


@check("M04_FONT_ANOMALY_IN_VALUES")
def font_anomaly(ctx: CheckContext) -> list[Finding]:
    """A value drawn in a font that the page's other transaction values do not use. Measured over
    the page, not one column: a short credit column would hide a single edited value."""
    if ctx.pdf is None or not ctx.pdf.value_fonts:
        return []
    policy = ctx.policy.structure.font_anomaly
    boxes = _boxes(ctx)
    pages: dict[int, list[ValueFont]] = defaultdict(list)
    for v in ctx.pdf.value_fonts:
        if _inside(v, boxes.get(v.page, [])):
            pages[v.page].append(v)
    out: list[Finding] = []
    for page, values in sorted(pages.items()):
        if len(values) < policy.min_values_on_page:
            continue
        counts = Counter(_font(v) for v in values)
        usual, _ = counts.most_common(1)[0]
        for v in values:
            share = counts[_font(v)] / len(values)
            if share >= 1 - float(policy.majority_share):
                continue
            out.append(
                ctx.finding(
                    "M04_FONT_ANOMALY_IN_VALUES",
                    f"{page}|{v.text}|{v.x0:.4f}|{v.top:.4f}",
                    category="STRUCTURE",
                    severity="HIGH",
                    title=f"One amount on page {page} is drawn in a different font",
                    facts={
                        "value": v.text,
                        "font": _font(v),
                        "usualFont": usual,
                        "shareOfPageValues": f"{share:.2f}",
                    },
                    evidence=[
                        Evidence(
                            doc_id=ctx.doc_id,
                            page=page,
                            bbox={"x0": v.x0, "y0": v.top, "x1": v.x1, "y1": v.bottom},
                            label="Different font",
                        )
                    ],
                )
            )
    return out


@check("M06_IMAGE_ONLY")
def image_only(ctx: CheckContext) -> list[Finding]:
    pages = [
        p.page_no for p in ctx.doc.pages if not p.blank and p.text_layer != TextLayerStatus.USABLE
    ]
    if not pages or not ctx.doc.content_type.endswith("pdf"):
        return []
    return [
        ctx.finding(
            "M06_IMAGE_ONLY",
            "pages",
            category="STRUCTURE",
            severity="INFO",
            title="Some pages are images without text, so they are read from the picture only",
            facts={"pages": ", ".join(map(str, pages))},
            evidence=[Evidence(doc_id=ctx.doc_id, page=pages[0], label="Image-only page")],
        )
    ]
