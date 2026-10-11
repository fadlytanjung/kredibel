"""Scenarios, tampering, duplicates, truth.json and fixtures (docs/18 §4–§7, AC-002-8…15)."""

import hashlib
import io
import json
from datetime import timedelta
from decimal import Decimal
from functools import cache

import imagehash
import pdfplumber
import pytest
from PIL import Image
from pypdf import PdfReader

from kredibel_synth import world
from kredibel_synth.cli import write_scenario
from kredibel_synth.fixtures import build_fixtures
from kredibel_synth.output import LEDGER_FILE
from kredibel_synth.pdf import pdf_date
from kredibel_synth.scenarios import Scenario, build
from kredibel_synth.truth import truth


@cache
def scenario(name: str, seed: int = 1) -> Scenario:
    return build(name, seed)


def _chars(pdf: bytes, page: int) -> list[dict]:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        return list(doc.pages[page - 1].chars)


def _text(pdf: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        return "\n".join(p.extract_text() or "" for p in doc.pages)


def test_ac002_1_s1_has_every_file_and_the_truth(tmp_path):
    folder = write_scenario(scenario("S1"), tmp_path)
    names = {p.name for p in folder.iterdir()}
    assert {"truth.json", "upload-order.txt", "README.md", LEDGER_FILE} <= names
    assert len([n for n in names if n.startswith("statement-")]) == 6
    assert len([n for n in names if n.startswith("inv-sales-")]) == 24
    assert len([n for n in names if n.startswith("inv-purchase-")]) == 16
    assert len([n for n in names if n.startswith("receipt-")]) == 24
    order = (folder / "upload-order.txt").read_text().split()
    assert sorted(order) == sorted(
        n for n in names if n not in {"truth.json", "upload-order.txt", "README.md"}
    )
    assert world.WATERMARK in (folder / "README.md").read_text()


def test_ac002_8_t1_is_a_second_revision_with_the_new_value_in_helvetica():
    sc = scenario("S2")
    pdf = sc.files["statement-2026-03.pdf"]
    assert pdf.count(b"%%EOF") == 2
    meta = PdfReader(io.BytesIO(pdf)).metadata
    assert meta is not None and meta["/Producer"] == "PDF Editor 11"
    record = next(t for t in sc.tampering if t.technique == "T1")
    page = sc.row_pages[record.details["rowKey"]]
    chars = _chars(pdf, page)
    edited = [c for c in chars if c["fontname"].endswith("Helvetica")]
    assert "".join(c["text"] for c in edited) == "7,250,000.00"
    text = _text(pdf)
    assert "1,250,000.00" not in text and "7,250,000.00" in text
    st = sc.books.statements["2026-03"]
    assert meta["/CreationDate"] == f"D:{st.created_at:%Y%m%d}020000+07'00'"
    assert meta["/ModDate"] == pdf_date(st.created_at + timedelta(days=3))
    # Balances were left untouched: the printed row no longer adds up.
    anchor = next(r for r in st.rows if r.key == record.details["rowKey"])
    assert f"{anchor.balance:,.2f}" in text


def test_ac002_8_other_scenarios_leave_march_untouched():
    assert scenario("S1").files["statement-2026-03.pdf"].count(b"%%EOF") == 1


def test_ac002_9_s3_duplicates():
    sc = scenario("S3")
    files = sc.files
    feb = files["statement-2026-02.pdf"]
    assert (
        hashlib.sha256(files["statement-2026-02 (1).pdf"]).digest() == hashlib.sha256(feb).digest()
    )
    reexport = files["statement-2026-02-reexport.pdf"]
    assert reexport != feb and _text(reexport) == _text(feb)
    [scan] = [n for n in files if n.endswith("-scan.pdf")]
    assert all(
        not (p.extract_text() or "").strip() for p in pdfplumber.open(io.BytesIO(files[scan])).pages
    )
    [again] = [n for n in files if n.endswith("-photo2.jpg")]
    original = again.replace("-photo2", "")
    a, b = (imagehash.phash(Image.open(io.BytesIO(files[n]))) for n in (original, again))
    assert a - b <= 8 and files[original] != files[again]
    ledger = files[LEDGER_FILE].decode().splitlines()[2:]
    copies = [e for e in sc.books.ledger if e.key in sc.ledger_duplicates]
    assert len(copies) >= 2 and len(ledger) == len(sc.books.ledger)
    first = copies[0]
    same = [
        e
        for e in sc.books.ledger
        if (e.date, e.account, e.amount, e.reference)
        == (first.date, first.account, first.amount, first.reference)
    ]
    assert len(same) == 2 and first.date >= world.T11_FROM


def test_ac002_10_s4_changed_supplier_account_and_unpaid_invoices():
    sc = scenario("S4")
    roastline = [i for i in sc.books.purchases if i.issuer == world.ROASTLINE.party]
    may = next(i for i in roastline if i.key == "inv-purchase-2026-05-03")
    assert may.pay_to.bank_name == world.SECOND_BANK
    assert {i.pay_to.account_number for i in roastline if i.issue_date < may.issue_date} == {
        "9900023318"
    }
    assert any(
        r.description.endswith(may.pay_to.account_number[-4:])
        for r in sc.books.bank_rows
        if r.documents == [may.key]
    )
    assert world.ROASTLINE_NEW_PAY_TO.account_number in _text(sc.files[may.file])
    bluewater = [i for i in sc.books.purchases if i.issuer == world.BLUEWATER.party]
    assert len(bluewater) == 2
    paid = {d for m in sc.books.matches for d in m.documents}
    assert not paid & {i.key for i in bluewater}
    assert not [e for e in sc.books.ledger if "Bluewater" in e.description]


def test_ac002_11_s5_is_s1_in_reverse_order():
    s1, s5 = scenario("S1"), scenario("S5")
    assert s1.files == s5.files
    assert s5.upload_order[:6] == [f"statement-2026-{m:02d}.pdf" for m in range(6, 0, -1)]
    assert s5.upload_order[6] == LEDGER_FILE
    assert sorted(s5.upload_order) == sorted(s1.upload_order)


@pytest.mark.parametrize("name", ["S1", "S2", "S3", "S4", "S5"])
def test_ac002_12_truth_follows_the_shape_of_docs_18(name: str):
    data = json.loads(json.dumps(truth(scenario(name))))
    assert {
        "scenario",
        "seed",
        "workspace",
        "uploadOrder",
        "documents",
        "matches",
        "months",
        "expectedSuggestions",
        "expectedCounterparties",
        "expectedFlows",
    } <= data.keys()
    assert "taxId" not in json.dumps(data["workspace"]) and "address" not in json.dumps(
        data["workspace"]
    )
    files = {d["file"] for d in data["documents"]}
    assert files == set(scenario(name).files)
    assert {m["expect"] for m in data["matches"]} == {"AUTO", "PROPOSED"}
    assert len(data["months"]) == 6
    declared = {data["workspace"]["profile"].get("taxId"), world.ACCOUNT}
    assert all(
        json.dumps(s["value"]) not in map(json.dumps, declared) for s in data["expectedSuggestions"]
    )


def test_truth_expectations_per_scenario():
    s1 = truth(scenario("S1"))["months"]
    assert [s1[m]["riskLevel"] for m in world.MONTHS] == [
        "LOW",
        "LOW",
        "LOW",
        "LOW",
        "LOW",
        "MEDIUM",
    ]
    assert s1["2026-02"]["reviewItems"] == {"PROPOSED_MATCH": 1}
    s2 = truth(scenario("S2"))
    march = next(d for d in s2["documents"] if d["file"] == "statement-2026-03.pdf")
    assert march["expected"]["verdict"] == "TAMPERED"
    assert march["tampering"][0]["after"] == "7250000.00"
    assert Decimal(s2["months"]["2026-03"]["figures"]["moneyIn"]) - Decimal(
        s1["2026-03"]["figures"]["moneyIn"]
    ) == Decimal("6000000")
    s3 = truth(scenario("S3"))["months"]
    assert all(s3[m]["figures"] == s1[m]["figures"] for m in world.MONTHS)  # nothing counted twice
    assert sum(s3[m]["reviewItems"].get("POSSIBLE_DUPLICATE", 0) for m in world.MONTHS) == 4
    s4 = truth(scenario("S4"))["months"]
    assert s4["2026-05"]["riskLevel"] == "HIGH" and s4["2026-04"]["reviewItems"] == {
        "UNMATCHED_DOCUMENT": 2
    }


def test_ac002_14_scan_variant_has_no_text_layer_and_the_same_truth():
    scanned = build("S1", 1, scan=True)
    for name, data in scanned.files.items():
        if name.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(data)) as doc:
                assert all(not (p.extract_text() or "").strip() for p in doc.pages), name
    original, other = truth(scenario("S1")), truth(scanned)
    assert original["matches"] == other["matches"] and original["months"] == other["months"]


def test_ac002_15_fixtures():
    fixtures = {fx.name: fx for fx in build_fixtures(1)}
    assert set(fixtures) == {
        "undeclared-account",
        "holder-mismatch",
        "regenerated-statement",
        "double-payment",
        "whiteout-overlay",
        "cid-glyphs",
        "gambling-and-returns",
        "ledger-xlsx",
    }
    white = fixtures["whiteout-overlay"]
    chars = [
        c
        for page in pdfplumber.open(io.BytesIO(white.files["statement-2026-03.pdf"])).pages
        for c in page.chars
    ]
    on_top = "".join(c["text"] for c in chars if c["fontname"].endswith("Helvetica"))
    assert on_top == white.expected["drawnOnTop"]
    near = [
        c
        for c in chars
        if not c["fontname"].endswith("Helvetica")
        and abs(c["top"] - next(h for h in chars if h["fontname"].endswith("Helvetica"))["top"]) < 1
    ]
    assert white.expected["underneath"] in "".join(c["text"] for c in near)
    cid = _text(fixtures["cid-glyphs"].files["statement-2026-03.pdf"])
    assert "(cid:" in cid or not any(ch.isdigit() for ch in cid)
    regenerated = fixtures["regenerated-statement"]
    meta = PdfReader(io.BytesIO(regenerated.files["statement-2026-05.pdf"])).metadata
    assert meta is not None and meta["/Producer"] == "PDF Editor 11"
    april, may = regenerated.documents
    assert may["opening"] != april["closing"]
    gambling = fixtures["gambling-and-returns"].documents[0]
    tags = [t for r in gambling["rows"] for t in r["riskTags"]]
    assert tags.count("RETURNED_ITEM") == 3 and "GAMBLING" in tags
    for fx in fixtures.values():
        assert json.dumps(fx.truth())


def test_ac002_2_generating_twice_gives_identical_files(tmp_path):
    first = write_scenario(build("S2", 3), tmp_path / "a")
    second = write_scenario(build("S2", 3), tmp_path / "b")

    def digest(folder):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}

    assert digest(first) == digest(second)
