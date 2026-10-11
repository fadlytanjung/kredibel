#!/usr/bin/env python3
"""Check that no Python string literal under backend/app/agents/ exceeds 200 characters.

See constitution Non-negotiable #10:
'Prompts live in backend/app/agents/prompts/*.md. No prompt text over 200 characters in Python.'
Acceptance criteria: AC-001-12.
"""

import ast
import sys
from pathlib import Path


def check_no_long_prompts(agents_dir: Path) -> list[str]:
    """Scan Python files in agents_dir (excluding prompts/) for string literals > 200 chars."""
    violations: list[str] = []

    if not agents_dir.exists():
        return violations

    for py_file in sorted(agents_dir.rglob("*.py")):
        # Skip files inside any 'prompts' directory
        if "prompts" in py_file.parts:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"{py_file}:{e.lineno}: syntax error {e.msg}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                char_count = len(node.value)
                if char_count > 200:
                    lineno = getattr(node, "lineno", 0)
                    violations.append(
                        f"{py_file}:{lineno}: string literal has {char_count} chars (limit 200)"
                    )

    return violations


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    agents_dir = repo_root / "backend" / "app" / "agents"

    violations = check_no_long_prompts(agents_dir)
    if violations:
        print("ERROR: Found Python string literals > 200 characters in agents/ (AC-001-12):")
        for v in violations:
            print(f"  {v}")
        print("\nFix: Move prompt text to backend/app/agents/prompts/*.md.")
        return 1

    print("OK: No string literals > 200 chars in backend/app/agents/ (AC-001-12).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
