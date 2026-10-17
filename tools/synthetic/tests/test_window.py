"""A window of the demo books (spec 024, AC-024-1): the files of the chosen months, the ledger rows
of those months, and the upload order without what was cut."""

import json

from kredibel_synth.window import keep_window

LEDGER = """# SYNTHETIC — FOR TESTING. LedgerLite 3 export, 01/06/2026 to 30/11/2026
Date,Journal,Account,Account Name,Description,Reference,Debit,Credit
01/07/2026,BNK-1,6050,Warehouse rent,Rent July,,15000000.00,
01/08/2026,BNK-2,6050,Warehouse rent,Rent August,,15000000.00,
15/10/2026,BNK-3,1110,Cash at bank,Sale,,,2000000.00
02/11/2026,BNK-4,6050,Warehouse rent,Rent November,,15000000.00,
"""


def test_ac024_1_only_the_window_s_files_and_ledger_rows_stay(tmp_path):
    names = [
        "statement-2026-07.pdf",
        "statement-2026-08.pdf",
        "inv-sales-2026-09-01.pdf",
        "receipt-2026-10-02.jpg",
        "receipt-2026-11-01-photo2.jpg",
        "statement-2026-08 (1).pdf",
    ]
    for name in names:
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "ledger-2026-06_2026-11.csv").write_text(LEDGER, encoding="utf-8")
    order = [*names, "ledger-2026-06_2026-11.csv"]
    (tmp_path / "upload-order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    (tmp_path / "truth.json").write_text(json.dumps({"uploadOrder": order}), encoding="utf-8")

    keep_window(tmp_path, "2026-08", "2026-10")

    kept = sorted(
        p.name for p in tmp_path.iterdir() if p.name not in ("upload-order.txt", "truth.json")
    )
    assert kept == [
        "inv-sales-2026-09-01.pdf",
        "ledger-2026-08_2026-10.csv",
        "receipt-2026-10-02.jpg",
        "statement-2026-08 (1).pdf",
        "statement-2026-08.pdf",
    ]
    ledger = (tmp_path / "ledger-2026-08_2026-10.csv").read_text(encoding="utf-8").splitlines()
    assert ledger[0].endswith("01/08/2026 to 31/10/2026")
    assert [row.split(",")[1] for row in ledger[2:]] == ["BNK-2", "BNK-3"]
    order_now = (tmp_path / "upload-order.txt").read_text(encoding="utf-8").splitlines()
    assert "ledger-2026-08_2026-10.csv" in order_now and "statement-2026-07.pdf" not in order_now
    truth = json.loads((tmp_path / "truth.json").read_text(encoding="utf-8"))
    assert truth["uploadOrder"] == [n for n in order_now]
