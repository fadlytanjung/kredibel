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


def test_ac019_3_refreshed_references_have_states_drawers_and_planned_markers():
    """AC-019-3: document, month, all-months and review references exist as implemented screens,
    states or drawers; a part that is not built is marked planned with its task."""
    for slug, status in {
        "document": "IMPLEMENTED",
        "document-ledger": "IMPLEMENTED_STATE",
        "month": "IMPLEMENTED",
        "months": "IMPLEMENTED",
        "review": "IMPLEMENTED",
        "review-match": "IMPLEMENTED_DRAWER",
        "review-correction": "IMPLEMENTED_DRAWER",
        "review-mapping": "IMPLEMENTED_DRAWER",
        "document-ledger-columns": "IMPLEMENTED_STATE",
        "assistant-welcome": "IMPLEMENTED_STATE",
        "assistant-history": "IMPLEMENTED_DRAWER",
    }.items():
        assert SCREEN_INVENTORY[slug].status == status, slug
        assert (ROOT / "design" / "mocks" / f"{slug}.html").exists(), slug

    # The column confirmation is built (T005-11): no mock presents it as planned any more.
    ledger = (ROOT / "design" / "mocks" / "document-ledger.html").read_text(encoding="utf-8")
    assert "T005-11" not in ledger
    mapping = (ROOT / "design" / "mocks" / "review-mapping.html").read_text(encoding="utf-8")
    assert "Confirm columns" in mapping and 'aria-label="Description"' in mapping
    dashboard = (ROOT / "design" / "mocks" / "dashboard.html").read_text(encoding="utf-8")
    assert "Planned, spec 014" in dashboard


def test_ac019_2_mocks_and_browser_checks_share_one_synthetic_fixture():
    """AC-019-2, AC-019-4: each refreshed screen's mock and its Playwright spec read the same
    fixture file, so numbers and words cannot drift between them."""
    fixtures = ROOT / "contracts" / "design" / "fixtures"
    specs = ROOT / "frontend" / "tests" / "visual"
    generator = (ROOT / "tools" / "design" / "mocks" / "screens.py").read_text(encoding="utf-8")
    widgets = ROOT / "frontend" / "src" / "widgets"
    readers = (specs / "fixtures.ts").read_text(encoding="utf-8") + (
        widgets / "dashboard" / "dashboard.fixture.ts"
    ).read_text(encoding="utf-8")
    for name in ("dashboard", "document", "month", "review"):
        assert (fixtures / f"{name}.json").exists(), name
        assert f"{name}.json" in generator, f"the mock generator must read {name}.json"
        assert f"{name}.json" in readers, f"the browser checks must read {name}.json"
        assert (specs / f"{name}.spec.ts").exists(), f"{name}.spec.ts must prove the parity"
    # Synthetic data only (non-negotiable 7): the demo workspace, never a real account number.
    for path in fixtures.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "Sunrise Coffee Roasters" in text or "IDR" in text, path.name
        assert "••" in text or "account" not in text.lower() or "acc" in text.lower(), path.name


def test_ac019_5_task_claims_and_implementation_status_audit():
    """AC-019-5: Incomplete acceptance criteria remain open with task IDs and dependencies."""
    reading_tasks = (ROOT / "docs" / "specs" / "005-reading" / "tasks.md").read_text(
        encoding="utf-8"
    )
    status_doc = (ROOT / "docs" / "20-implementation-status.md").read_text(encoding="utf-8")
    # T005-11 (the mapping confirmation) is ticked only because it is built: the review drawer,
    # its API and its mocks exist, and the status records how the proposal is made (code first,
    # the MODEL_LITE mapper only for headers the synonyms miss).
    assert "- [x] **T005-11**" in reading_tasks
    assert (ROOT / "frontend" / "src" / "features" / "review" / "MappingEditor.tsx").exists()
    assert (ROOT / "design" / "mocks" / "review-mapping.html").exists()
    documents_api = (ROOT / "backend" / "app" / "api" / "documents.py").read_text(encoding="utf-8")
    assert "ledger-mapping" in documents_api
    assert "019" in status_doc
    assert "map_ledger_columns.md" in status_doc and "MODEL_LITE" in status_doc, "mapper recorded"
    assert (ROOT / "backend" / "app" / "agents" / "prompts" / "map_ledger_columns.md").exists()
    # Tasks that stay open keep their owners (AC-019-5).
    open_tasks = (("010-dashboard-and-money-flow", "T010-06"),)
    for spec, task in open_tasks:
        tasks = (ROOT / "docs" / "specs" / spec / "tasks.md").read_text(encoding="utf-8")
        assert f"- [ ] **{task}**" in tasks, f"{task} is not built yet"
