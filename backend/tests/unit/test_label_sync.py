"""A month's labels from the stored books (spec 016, AC-016-1, AC-016-2): every categorized line,
document and unsettled value; rules and matches are not doubted; a person's category from the month
page becomes their decision; only new or moved values are written. Synthetic data only."""

from datetime import UTC, date, datetime
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_category_policy, load_learning_policy
from app.domain.label_sync import changed, month_labels
from app.domain.labels import AiDecision, LabelSubject, label_id, propose
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocStatus, DocType, Document

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts/policy"
POLICY = load_learning_policy(POLICY_DIR)
CATEGORIES = load_category_policy(POLICY_DIR / "categories.v1.yaml", POLICY_DIR)
AT = datetime(2026, 7, 2, tzinfo=UTC)


def line(
    tx: str, category: str, by: str, confidence: str | None = None, consensus=None
) -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_mar",
        page=2,
        row_index=int(tx[-1]),
        date=date(2026, 3, 10),
        month="2026-03",
        description=f"{tx.upper()} TO 0081234567720\nREF",
        amount=D("-100.00"),
        balance=None,
        category=category,
        categorized_by=by,
        category_confidence=D(confidence) if confidence else None,
        consensus=consensus or {},
    )


DOC = Document(
    doc_id="doc_mar",
    file_name="ACB_Mar_2026.pdf",
    content_type="application/pdf",
    size_bytes=1,
    page_count=3,
    sha256="a" * 64,
    gcs_path="gs://synthetic/doc_mar.pdf",
    uploaded_by="u-1",
    uploaded_at=AT,
    doc_type=DocType.BANK_STATEMENT,
    type_confidence=D("0.99"),
    status=DocStatus.DONE,
    months=["2026-03"],
)
LINES = [
    line("tx_1", "RENT", "MODEL", "0.66"),
    line("tx_2", "BANK_FEES", "RULE"),
    line("tx_3", "INVENTORY_PURCHASE", "MATCH"),
    line("tx_4", "PAYROLL", "USER"),
    line("tx_5", "UNKNOWN", "NONE"),
    line(
        "tx_6",
        "OTHER_OPERATING_EXPENSE",
        "MODEL",
        "0.91",
        consensus={
            "amount": {
                "status": "CONFLICT",
                "page": 2,
                "raw": {"GEMINI": "100.00", "TEXT_LAYER": "160.00"},
            },
            "date": {
                "status": "AGREED",
                "page": 2,
                "raw": {"GEMINI": "10/03", "TEXT_LAYER": "10/03"},
            },
        },
    ),
]


def build():
    return month_labels(
        lines=LINES,
        docs=[DOC],
        invoices=[],
        receipts=[],
        policy=POLICY,
        categories=CATEGORIES,
        framework="IFRS",
        at=AT,
    )


def test_ac016_1_every_categorized_line_document_and_unsettled_value_is_a_label():
    labels = build()
    by = {(lb.task, lb.subject.tx_id or lb.subject.doc_id, lb.subject.field): lb for lb in labels}
    cats = {str(k[1]): lb for k, lb in by.items() if k[0] == "CATEGORY"}
    assert sorted(cats) == ["tx_1", "tx_2", "tx_3", "tx_4", "tx_6"], "UNKNOWN is no label"
    assert cats["tx_1"].ai.source == "MODEL" and cats["tx_1"].needs_check
    assert cats["tx_2"].ai.source == "RULE" and not cats["tx_2"].needs_check, (
        "a rule is not doubted"
    )
    assert cats["tx_3"].ai.source == "MATCH" and not cats["tx_3"].needs_check
    assert cats["tx_4"].status == "VERIFIED" and cats["tx_4"].final_source == "PERSON"
    assert cats["tx_1"].cashflow_class == "OPERATING" and cats["tx_1"].framework == "IFRS"
    assert cats["tx_1"].subject.display == "TX_1 TO 0081234567720"
    assert cats["tx_1"].example_text == "TX_1 TO ••••7720", "examples are masked"
    [doc] = [lb for lb in labels if lb.task == "DOC_TYPE"]
    assert doc.final_value == "BANK_STATEMENT" and not doc.needs_check
    [value] = [lb for lb in labels if lb.task == "FIELD_VALUE"]
    assert value.subject.field == "amount" and value.ai.value == "100.00" and value.needs_check
    assert value.subject.display == "ACB_Mar_2026.pdf, row 6 · amount"
    assert build() == labels, "deterministic"


def test_ac016_2_only_new_or_moved_values_are_written_and_people_win():
    fresh = build()
    stored = {lb.label_id: lb for lb in fresh}
    assert changed(fresh, stored, at=AT) == [], "nothing new, nothing moved"
    # A node wrote the label first with its provenance: a rebuilt copy never replaces it.
    node_label = propose(
        "CATEGORY",
        LabelSubject(display="x", doc_id="doc_mar", page_no=2, tx_id="tx_1"),
        AiDecision(
            value="RENT", source="MODEL", at=AT, confidence=D("0.66"), model="m", run_id="run_1"
        ),
        policy=POLICY,
    )
    assert changed(fresh, {**stored, node_label.label_id: node_label}, at=AT) == []
    # A match moved tx_3's category: the new automatic value is written.
    moved = [lb for lb in fresh if lb.subject.tx_id == "tx_3" and lb.task == "CATEGORY"]
    older = propose(
        "CATEGORY",
        moved[0].subject,
        AiDecision(value="SUPPLIER_PAYMENT", source="MODEL", at=AT, confidence=D("0.7")),
        policy=POLICY,
    )
    [written] = changed(fresh, {**stored, older.label_id: older}, at=AT)
    assert written.final_value == "INVENTORY_PURCHASE"
    # A person's category from the month page over a proposed label becomes their correction.
    tx4 = label_id("CATEGORY", LabelSubject(display="", doc_id="doc_mar", page_no=2, tx_id="tx_4"))
    proposed = propose(
        "CATEGORY",
        LabelSubject(display="x", doc_id="doc_mar", page_no=2, tx_id="tx_4"),
        AiDecision(value="RENT", source="MODEL", at=AT, confidence=D("0.8")),
        policy=POLICY,
    )
    assert proposed.label_id == tx4
    [person] = changed(fresh, {**stored, tx4: proposed}, at=AT)
    assert (
        person.status == "CORRECTED"
        and person.final_value == "PAYROLL"
        and person.ai.value == "RENT"
    )
