"""Select an unchanged S1 subset for the backend workflow replay (spec 007, T007-08a).

Run from tools/synthetic: uv run python reconciliation_fixtures.py.
Regenerates the books first; truth and files are selected together, never hand-edited.
"""

import json
from pathlib import Path

from kredibel_synth.render_receipt import render_receipt_pdf
from kredibel_synth.scenarios import build
from kredibel_synth.truth import truth

FILES = {
    "statement-2026-03.pdf",
    "inv-sales-2026-03-01.pdf",
    "inv-purchase-2026-03-01.pdf",
    "receipt-2026-03-02.pdf",
    "receipt-2026-03-01.pdf",
}


def main() -> None:
    scenario = build("S1", 1)
    # The card receipt's same generated values as a text PDF, so offline replay needs no OCR.
    card = next(r for r in scenario.books.receipts if r.key == "receipt-2026-03-01")
    card.form = "pdf"
    scenario.files[card.file] = render_receipt_pdf(card)
    source = truth(scenario)
    selected = [d for d in source["documents"] if d["file"] in FILES]
    assert len(selected) == len(FILES)
    folder = Path(__file__).resolve().parents[2] / "backend/tests/fixtures/reconciliation"
    folder.mkdir(parents=True, exist_ok=True)
    for name in sorted(FILES):
        (folder / name).write_bytes(scenario.files[name])
    (folder / "truth.json").write_text(
        json.dumps(
            {"scenario": "S1", "seed": 1, "documents": selected}, indent=2, ensure_ascii=False
        ) + "\n", encoding="utf-8",
    )
    print(f"Generated {len(FILES)} synthetic PDFs and their truth in {folder}")


if __name__ == "__main__":
    main()
