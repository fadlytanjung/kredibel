#!/usr/bin/env python3
"""Check for Firestore persistence model schema drift and generate schema snapshots.

Normative references: docs/22-data-migrations.md §10, docs/specs/001-foundation/tasks.md T001-32, AC-001-21.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "backend" / "app" / "adapters" / "firestore" / "models"
SNAPSHOT_FILE = ROOT / "contracts" / "data" / "schema-snapshot.json"


def get_annotation_str(node: ast.AST) -> str:
    """Convert an AST annotation node to its string representation."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Attribute):
        return f"{get_annotation_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{get_annotation_str(node.value)}[{get_annotation_str(node.slice)}]"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return f"{get_annotation_str(node.left)} | {get_annotation_str(node.right)}"
    if isinstance(node, ast.Tuple):
        return ", ".join(get_annotation_str(e) for e in node.elts)
    return ast.unparse(node)


def inspect_models(models_dir: Path) -> dict[str, Any]:
    """Parse all models in models_dir using AST into a canonical schema dictionary."""
    schema: dict[str, Any] = {}

    if not models_dir.exists():
        return schema

    for py_file in sorted(models_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue

        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for item in tree.body:
            if not isinstance(item, ast.ClassDef):
                continue

            class_name = item.name
            fields: dict[str, str] = {}
            schema_version: int | None = None

            for stmt in item.body:
                # ClassVar SCHEMA_VERSION = N
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "SCHEMA_VERSION":
                            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, int):
                                schema_version = stmt.value.value
                elif isinstance(stmt, ast.AnnAssign):
                    if isinstance(stmt.target, ast.Name):
                        field_name = stmt.target.id
                        if field_name == "SCHEMA_VERSION":
                            if stmt.value and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, int):
                                schema_version = stmt.value.value
                        elif field_name != "model_config":
                            fields[field_name] = get_annotation_str(stmt.annotation)

            # Store class details
            schema[class_name] = {
                "file": py_file.name,
                "schemaVersion": schema_version,
                "fields": dict(sorted(fields.items())),
            }

    return dict(sorted(schema.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="Write snapshot to contracts/data/schema-snapshot.json")
    args = parser.parse_args()

    current_schema = inspect_models(MODELS_DIR)
    current_json = json.dumps(current_schema, indent=2, sort_keys=True) + "\n"

    if args.write:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(current_json, encoding="utf-8")
        print(f"Wrote schema snapshot to {SNAPSHOT_FILE.relative_to(ROOT)} ({len(current_schema)} models)")
        return 0

    if not SNAPSHOT_FILE.exists():
        print(
            f"ERROR: Schema snapshot {SNAPSHOT_FILE.relative_to(ROOT)} does not exist. Run `make schema-snapshot`.",
            file=sys.stderr,
        )
        return 1

    stored_json = SNAPSHOT_FILE.read_text(encoding="utf-8")
    if current_json != stored_json:
        print(
            "ERROR: Firestore persistence model drift detected! (AC-001-21)\n"
            "The models in backend/app/adapters/firestore/models/ differ from contracts/data/schema-snapshot.json.\n"
            "If this change is intentional, follow docs/22-data-migrations.md and run `make schema-snapshot`.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: Persistence schema matches {SNAPSHOT_FILE.relative_to(ROOT)} (AC-001-21).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
