#!/usr/bin/env python3
"""Fail if generated mocks differ from their sources (AC-018-7); never rewrites the worktree."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    source = ROOT / 'tools/design/mocks/build_mocks.py'
    spec = importlib.util.spec_from_file_location('build_mocks', source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp:
        module.MOCKS = Path(temp)
        with contextlib.redirect_stdout(io.StringIO()):
            module.main()
        stale = []
        for file in sorted(Path(temp).rglob('*')):
            if file.is_file():
                actual = ROOT / 'design/mocks' / file.relative_to(temp)
                if not actual.exists() or file.read_bytes() != actual.read_bytes():
                    stale.append(str(actual.relative_to(ROOT)))
        if stale:
            print('Stale mocks: run make mocks and review screenshots.\n' + '\n'.join(stale))
            return 1
    print('OK: generated mocks match their sources (AC-018-7).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
