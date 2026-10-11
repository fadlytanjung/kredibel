"""Tests for tools/checks/no_long_prompts.py (AC-001-12)."""

import tempfile
from pathlib import Path

from tools.checks.no_long_prompts import check_no_long_prompts


def test_ac001_12_short_string_literals_pass():
    """String literals <= 200 characters under agents/ pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agent_file = tmp_path / "backend" / "app" / "agents" / "node.py"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text('SHORT = "' + "a" * 200 + '"\n')

        violations = check_no_long_prompts(tmp_path / "backend" / "app" / "agents")
        assert len(violations) == 0


def test_ac001_12_string_literal_over_200_chars_fails():
    """String literals > 200 characters under agents/ outside prompts/ fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        agent_file = tmp_path / "backend" / "app" / "agents" / "node.py"
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        agent_file.write_text('LONG = "' + "a" * 201 + '"\n')

        violations = check_no_long_prompts(tmp_path / "backend" / "app" / "agents")
        assert len(violations) == 1
        assert "201 chars" in violations[0]


def test_ac001_12_prompts_dir_is_exempt():
    """String literals inside prompts/ are exempt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        prompt_file = tmp_path / "backend" / "app" / "agents" / "prompts" / "prompt.py"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text('PROMPT = "' + "a" * 300 + '"\n')

        violations = check_no_long_prompts(tmp_path / "backend" / "app" / "agents")
        assert len(violations) == 0
