"""Tests for tools/checks/no_raw_styles.py (AC-001-18)."""

import tempfile
from pathlib import Path

from tools.checks.no_raw_styles import check_no_raw_styles


def test_ac001_18_tokens_and_tailwind_classes_pass():
    """Valid token usage and standard Tailwind classes pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "Button.tsx"
        code = (
            "export const Button = () => "
            '<button className="bg-brand text-ink p-4 rounded-sm">Click</button>;\n'
        )
        comp_file.write_text(code)

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) == 0


def test_ac001_18_hex_colour_fails():
    """Raw hex colors (e.g. #ff0000 or #fff) fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "BadColor.tsx"
        comp_file.write_text(
            'export const Bad = () => <div className="text-[#16212B]">Bad</div>;\n'
        )

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) >= 1
        assert any("#16212B" in v for v in violations)


def test_ac001_18_rgb_and_hsl_colour_fails():
    """rgb(), rgba(), hsl(), hsla() fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "BadRgb.tsx"
        comp_file.write_text(
            'export const Bad = () => <div className="bg-[rgb(0,0,0)]">Bad</div>;\n'
        )

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) >= 1
        assert any("rgb(" in v for v in violations)


def test_ac001_18_arbitrary_tailwind_dimension_fails():
    """Arbitrary Tailwind values like [13px] fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "BadDim.tsx"
        comp_file.write_text(
            'export const Bad = () => <div className="p-[13px] m-[5px]">Bad</div>;\n'
        )

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) >= 1
        assert any("[13px]" in v for v in violations)


def test_ac001_18_inline_style_outside_allowlist_fails():
    """Inline style= prop without allowlist / comment fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "BadStyle.tsx"
        comp_file.write_text(
            'export const Bad = () => <div style={{ fontSize: "16px" }}>Bad</div>;\n'
        )

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) >= 1
        assert any("style=" in v for v in violations)


def test_ac001_18_allowed_style_geometry_passes():
    """Computed geometry in charts or explicitly allowed styles pass."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        comp_file = tmp_path / "ChartBar.tsx"
        comp_file.write_text(
            "export const Bar = ({ width }: { width: number }) => (\n"
            "  <i style={{ width: `${width}%` }} /* allow-raw-style: computed geometry */ />\n"
            ");\n"
        )

        violations = check_no_raw_styles(tmp_path)
        assert len(violations) == 0
