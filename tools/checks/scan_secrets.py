#!/usr/bin/env python3
"""Scan repository files for leaked secrets, credentials, and private keys.

Constitution Non-negotiables #8:
'No secrets in the repo, image, logs or tool output. Google access uses service accounts (ADC).'
"""

import re
import sys
from pathlib import Path

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "Private key header"),
    (re.compile(r'"type":\s*"service_account"'), "Google service account JSON"),
    (re.compile(r"AIzaSy[0-9A-Za-z_-]{33}"), "Google API Key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
    (re.compile(r"ghp_[0-9a-zA-Z]{36}"), "GitHub Personal Access Token"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "Slack token"),
    # password = "…", password: '…', setPassword('…'); empty strings and i18n keys pass.
    (
        re.compile(r"""(?i)\b(?:set)?passw(?:or)?d\b\s*[:=(]\s*['"][^'"\s]{4,}['"]"""),
        "Hard-coded password",
    ),
]

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "storybook-static",
    "test-results",
    "playwright-report",
    "coverage",
    ".hypothesis",
}

IGNORED_FILES = {
    ".env",
    ".env.example",
    "uv.lock",
    "package-lock.json",
}


def is_binary_file(filepath: Path) -> bool:
    """Check if file appears to be binary."""
    try:
        with filepath.open("rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except Exception:
        return True


def scan_path_for_secrets(root_path: Path) -> list[str]:
    """Scan directory recursively for potential secret leaks."""
    findings: list[str] = []

    for path in sorted(root_path.rglob("*")):
        if path.is_dir():
            continue

        # Skip ignored directories
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        # Skip ignored files
        if path.name in IGNORED_FILES or (path.name.startswith(".env") and path.name != ".env.example"):
            continue

        # Skip binaries
        if is_binary_file(path):
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            for pattern, desc in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path}:{lineno}: detected {desc}")

    return findings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    findings = scan_path_for_secrets(repo_root)

    if findings:
        print("ERROR: Potential secrets detected in repository files:")
        for f in findings:
            print(f"  {f}")
        print("\nFix: Remove the secret immediately. Use environment variables / ADC instead.")
        return 1

    print("OK: No secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
