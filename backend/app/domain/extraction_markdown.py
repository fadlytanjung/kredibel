"""The page as Kredibel read it, in Markdown (spec 016, T016-04, AC-016-4; docs/09 §5). Pure.

One file per read page: the document and its type, the reading method and agreement, every value
with the model's reading and the text layer's, and the witness words. Account and ID numbers are
masked in values and witness text alike; amounts and dates stay as printed.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.accounts import mask_numbers_in_text

STATUS_WORD = {
    "AGREED": "agreed",
    "SINGLE_SOURCE": "one reading",
    "CONFLICT": "conflict",
    "MISSING": "missing",
}
NONE = "—"


@dataclass(frozen=True)
class ValueReading:
    name: str
    status: str
    model: str | None
    text_layer: str | None


@dataclass(frozen=True)
class RecordReading:
    title: str
    values: list[ValueReading] = field(default_factory=list)


@dataclass(frozen=True)
class PageExtraction:
    file_name: str
    page_no: int
    page_count: int
    doc_type: str
    type_confidence: Decimal | None
    method: str
    agreement: Decimal | None
    model: str | None
    prompt_version: str | None
    records: list[RecordReading]
    witness_text: str


def _cell(value: str | None) -> str:
    if value is None or not str(value).strip():
        return NONE
    text = " ".join(mask_numbers_in_text(str(value)).split())
    return text.replace("|", "\\|")


def page_markdown(page: PageExtraction) -> str:
    """The extraction file of one page; deterministic for the same inputs."""
    head = [f"# {page.file_name}, page {page.page_no} of {max(page.page_count, page.page_no)}"]
    kind = page.doc_type + (
        f" ({page.type_confidence:.2f})" if page.type_confidence is not None else ""
    )
    head.append(f"Document type: {kind}")
    head.append("Page type: not classified yet")
    reading = [page.method]
    if page.agreement is not None:
        reading.append(f"agreement {page.agreement:.2f}")
    if page.model:
        reading.append(f"model {page.model}")
    if page.prompt_version:
        reading.append(f"prompt {page.prompt_version}")
    head.append("Reading: " + ", ".join(reading))
    out = [*head, "", "## Values", ""]
    rows = [
        f"| {_cell(r.title)} | {_cell(v.name)} | {STATUS_WORD.get(v.status, v.status.lower())} "
        f"| {_cell(v.model)} | {_cell(v.text_layer)} |"
        for r in page.records
        for v in r.values
    ]
    if rows:
        out += [
            "| Record | Field | Readings | Model | Text layer |",
            "|---|---|---|---|---|",
            *rows,
        ]
    else:
        out.append("No values were read on this page.")
    out += ["", "## Witness text", ""]
    witness = mask_numbers_in_text(page.witness_text).strip()
    if witness:
        out += ["```text", witness, "```"]
    else:
        out.append("No text layer or OCR words on this page; it was read from its image only.")
    return "\n".join(out) + "\n"
