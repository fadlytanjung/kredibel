"""A window of the demo books (spec 024, AC-024-1): only the files of the chosen months and the
ledger export cut to them, so the demo shows three months without the rest of the half-year."""

from __future__ import annotations

import calendar
import json
import re
from pathlib import Path

MONTH = re.compile(r"(\d{4})-(\d{2})")
PERIOD = re.compile(r"\d{2}/\d{2}/\d{4} to \d{2}/\d{2}/\d{4}")
KEEP = {"README.md", "truth.json", "upload-order.txt"}


def _month(name: str) -> str | None:
    found = MONTH.search(name)
    return f"{found.group(1)}-{found.group(2)}" if found else None


def _row_month(row: str) -> str | None:
    day = row.split(",", 1)[0]
    parts = day.split("/")
    return f"{parts[2]}-{parts[1]}" if len(parts) == 3 and parts[2].isdigit() else None


def _cut_ledger(path: Path, start: str, end: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    year, month = (int(x) for x in end.split("-"))
    last = calendar.monthrange(year, month)[1]
    period = f"01/{start[5:]}/{start[:4]} to {last:02d}/{end[5:]}/{end[:4]}"
    out: list[str] = []
    for line in lines:
        if line.startswith("#"):
            out.append(PERIOD.sub(period, line))
            continue
        month_of = _row_month(line)
        if month_of is None or start <= month_of <= end:
            out.append(line)  # the header, and the rows of the window
    name = f"ledger-{start}_{end}{path.suffix}"
    path.unlink()
    (path.parent / name).write_text("\n".join(out) + "\n", encoding="utf-8")
    return name


def keep_window(folder: Path, start: str, end: str) -> None:
    """Removes every file of a month outside [start, end] (yyyy-mm), cuts the ledger export to the
    window, and keeps the upload order (upload-order.txt and truth.json) to what is left."""
    renamed: dict[str, str] = {}
    for path in sorted(folder.iterdir()):
        if path.name in KEEP or not path.is_file():
            continue
        if path.name.startswith("ledger-") and path.suffix == ".csv":
            renamed[path.name] = _cut_ledger(path, start, end)
            continue
        month = _month(path.name)
        if month is not None and not start <= month <= end:
            path.unlink()
    present = {p.name for p in folder.iterdir()}

    def kept(names: list[str]) -> list[str]:
        return [renamed.get(n, n) for n in names if renamed.get(n, n) in present]

    order_file = folder / "upload-order.txt"
    if order_file.exists():
        names = [n for n in order_file.read_text(encoding="utf-8").split("\n") if n.strip()]
        order_file.write_text("\n".join(kept(names)) + "\n", encoding="utf-8")
    truth_file = folder / "truth.json"
    if truth_file.exists():
        truth = json.loads(truth_file.read_text(encoding="utf-8"))
        raw = truth.get("uploadOrder") or []
        names = [x if isinstance(x, str) else x["file"] for x in raw]
        keep = set(kept(names))
        truth["uploadOrder"] = [
            (
                renamed.get(x, x)
                if isinstance(x, str)
                else {**x, "file": renamed.get(x["file"], x["file"])}
            )
            for x in raw
            if renamed.get(
                x if isinstance(x, str) else x["file"], x if isinstance(x, str) else x["file"]
            )
            in keep
        ]
        truth["window"] = {"from": start, "to": end}
        truth_file.write_text(
            json.dumps(truth, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
