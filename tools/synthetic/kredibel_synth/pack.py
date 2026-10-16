"""One demo pack from the scenarios (spec 024): the base scenario's books, each later scenario's
version of a file in its place and its new files added, so a workspace holds one coherent set of
books with the planted findings (an edited statement, a diverted payment, unpaid invoices, a scanned
copy) instead of two versions of a statement. The ledger stays the base scenario's."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

SKIP = {"README.md", "truth.json", "upload-order.txt"}
KIND = {"inv-sales": 0, "inv-purchase": 1, "receipt": 2, "statement": 3}
MONTH = re.compile(r"(\d{4}-\d{2})")


def _key(name: str) -> tuple[int, str, int, str]:
    if name.startswith("ledger-"):
        return (0, "", 0, name)
    found = MONTH.search(name)
    kind = next((rank for prefix, rank in KIND.items() if name.startswith(prefix)), 9)
    return (1, found.group(1) if found else "9999-99", kind, Path(name).stem)


def make_pack(out: Path, scenarios: tuple[str, ...]) -> Path:
    base = out / scenarios[0] / "seed-1"
    pack = out / "pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir(parents=True)
    for path in base.iterdir():
        if path.is_file() and path.name not in SKIP:
            shutil.copyfile(path, pack / path.name)
    for scenario in scenarios[1:]:
        folder = out / scenario / "seed-1"
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.name in SKIP or path.name.startswith("ledger-"):
                continue
            target = pack / path.name
            if not target.exists() or target.read_bytes() != path.read_bytes():
                shutil.copyfile(path, target)
    order = sorted((p.name for p in pack.iterdir() if p.is_file()), key=_key)
    truth = json.loads((base / "truth.json").read_text(encoding="utf-8"))
    truth["uploadOrder"] = order
    truth["pack"] = list(scenarios)
    (pack / "truth.json").write_text(
        json.dumps(truth, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (pack / "upload-order.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    (pack / "README.md").write_text(
        "# Demo pack — SYNTHETIC, FOR TESTING\n\n"
        f"Sunrise Coffee Roasters' books from {', '.join(scenarios)} in one set (spec 024): "
        "upload the files in `upload-order.txt`, the ledger first, then map the bank account "
        "to ledger account 1110 in Settings.\n",
        encoding="utf-8",
    )
    return pack
