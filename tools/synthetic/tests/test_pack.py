"""One demo pack from the scenarios (spec 024): S1's books with each later scenario's version of a
file in its place and its new files added, the ledger kept from S1, in month order."""

import json

from kredibel_synth.pack import make_pack


def _scenario(root, name, files):
    folder = root / name / "seed-1"
    folder.mkdir(parents=True)
    for file, content in files.items():
        (folder / file).write_bytes(content)
    (folder / "truth.json").write_text(
        json.dumps({"workspace": {"name": "x"}, "uploadOrder": list(files)})
    )
    return folder


def test_ac024_1_the_pack_replaces_and_adds_what_each_scenario_changes(tmp_path):
    _scenario(
        tmp_path,
        "S1",
        {
            "ledger-2026-08_2026-10.csv": b"base ledger",
            "inv-sales-2026-08-01.pdf": b"a",
            "statement-2026-08.pdf": b"original",
            "statement-2026-10.pdf": b"original oct",
        },
    )
    _scenario(
        tmp_path, "S2", {"statement-2026-08.pdf": b"edited", "inv-sales-2026-08-01.pdf": b"a"}
    )
    _scenario(
        tmp_path,
        "S3",
        {"inv-sales-2026-08-01-scan.pdf": b"scan", "ledger-2026-08_2026-10.csv": b"keyed twice"},
    )
    _scenario(
        tmp_path,
        "S4",
        {"statement-2026-10.pdf": b"diverted", "inv-purchase-2026-09-04.pdf": b"unpaid"},
    )

    pack = make_pack(tmp_path, ("S1", "S2", "S3", "S4"))

    assert (pack / "statement-2026-08.pdf").read_bytes() == b"edited"
    assert (pack / "statement-2026-10.pdf").read_bytes() == b"diverted"
    assert (pack / "ledger-2026-08_2026-10.csv").read_bytes() == b"base ledger"
    order = json.loads((pack / "truth.json").read_text())["uploadOrder"]
    assert order == [
        "ledger-2026-08_2026-10.csv",
        "inv-sales-2026-08-01.pdf",
        "inv-sales-2026-08-01-scan.pdf",
        "statement-2026-08.pdf",
        "inv-purchase-2026-09-04.pdf",
        "statement-2026-10.pdf",
    ]
    assert (pack / "upload-order.txt").read_text().splitlines() == order
