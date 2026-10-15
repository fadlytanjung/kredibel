# pyright: reportMissingImports=false
"""Tests for Spec 019: Current UI and mock parity (AC-019-1, AC-019-5).

Verifies:
- AC-019-1: The mock index and every screen display identifiable route and implementation status.
  Planned screens (clients, labels, runs) remain marked as design-only (P1).
- AC-019-5: Implementation status and task claims match audited reality: incomplete acceptance
  criteria remain open with task IDs and dependencies.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MOCKS_TOOL_DIR = ROOT / "tools" / "design" / "mocks"
if str(MOCKS_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(MOCKS_TOOL_DIR))

from inventory import SCREEN_INVENTORY, ScreenInfo  # noqa: E402


def test_ac019_1_screen_inventory_covers_all_screens():
    """AC-019-1: Every mock screen has an inventory entry with route, status, and spec."""
    from build_mocks import SCREENS  # noqa: E402

    for slug in SCREENS:
        assert slug in SCREEN_INVENTORY, f"Missing inventory entry for screen {slug}"
        info: ScreenInfo = SCREEN_INVENTORY[slug]
        assert info.slug == slug
        assert info.route, f"Screen {slug} must have a corresponding route"
        assert info.status in (
            "IMPLEMENTED",
            "IMPLEMENTED_STATE",
            "IMPLEMENTED_DRAWER",
            "IMPLEMENTED_OVERLAY",
            "SYNTHETIC_PREVIEW",
            "DESIGN_ONLY",
        )
        assert info.spec, f"Screen {slug} must reference its spec"
        assert info.badge_label, f"Screen {slug} must have a badge label"


def test_ac019_1_planned_screens_marked_design_only():
    """AC-019-1: Planned clients/suppliers, Labels, and Runs remain marked as design-only."""
    design_only_slugs = {"clients", "labels", "runs"}
    for slug in design_only_slugs:
        assert slug in SCREEN_INVENTORY, f"{slug} must be in inventory"
        info = SCREEN_INVENTORY[slug]
        assert info.status == "DESIGN_ONLY", f"{slug} must be marked DESIGN_ONLY"
        assert "Design only" in info.badge_label
        assert "P1" in info.badge_label

    # Verify that in the React app, these routes are placeholders
    router_ts = (ROOT / "frontend" / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
    assert "CounterpartiesPage" in router_ts
    assert "LabelsPage" in router_ts
    assert "RunsPage" in router_ts


def test_ac019_1_mock_index_renders_route_and_status():
    """AC-019-1: The generated mock index (design/mocks/index.html) displays route & status."""
    index_html_path = ROOT / "design" / "mocks" / "index.html"
    assert index_html_path.exists(), "design/mocks/index.html must exist"
    content = index_html_path.read_text(encoding="utf-8")

    # Index must show status badges and route tags
    assert "badge" in content
    assert "Design only (P1)" in content
    assert "Implemented" in content
    assert "/counterparties" in content
    assert "/labels" in content
    assert "/runs" in content


def test_ac019_1_opened_screens_identify_status_and_route():
    """AC-019-1: Opened screens display implementation status and route in markup."""
    mocks_dir = ROOT / "design" / "mocks"

    # Check key design-only screens
    for slug in ("clients", "labels", "runs"):
        html_file = mocks_dir / f"{slug}.html"
        assert html_file.exists(), f"{html_file} must exist"
        html = html_file.read_text(encoding="utf-8")
        assert "Design only (P1)" in html, f"{slug}.html must display Design only (P1)"
        info = SCREEN_INVENTORY[slug]
        assert info.route in html, f"{slug}.html must display route {info.route}"

    # Check implemented screens
    for slug in ("dashboard", "documents", "review", "profit-loss"):
        html_file = mocks_dir / f"{slug}.html"
        assert html_file.exists(), f"{html_file} must exist"
        html = html_file.read_text(encoding="utf-8")
        assert "Implemented" in html, f"{slug}.html must display Implemented"
        info = SCREEN_INVENTORY[slug]
        assert info.route in html, f"{slug}.html must display route {info.route}"


def test_ac019_5_task_claims_and_implementation_status_audit():
    """AC-019-5: Incomplete acceptance criteria remain open with task IDs and dependencies."""
    reading_tasks = (ROOT / "docs" / "specs" / "005-reading" / "tasks.md").read_text(
        encoding="utf-8"
    )
    # T005-11 (mapping confirmation UI) must remain open until built
    assert "- [ ] **T005-11**" in reading_tasks

    status_doc = (ROOT / "docs" / "20-implementation-status.md").read_text(encoding="utf-8")
    # Ledger import status should accurately note mapping confirmation UI is open / in progress
    assert "019" in status_doc
    assert "T005-11" in status_doc or "confirmation" in status_doc
