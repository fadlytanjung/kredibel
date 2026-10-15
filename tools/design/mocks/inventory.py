"""Screen inventory and implementation status for Kredibel mocks (AC-019-1).

Tracks the correspondence between high-fidelity mocks in design/mocks/ and actual
routes / components in the frontend React application (frontend/src/app/router.tsx).
Distinguishes implemented screens from design-only P1 proposals (Clients, Labels, Runs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ScreenStatus = Literal[
    "IMPLEMENTED",
    "IMPLEMENTED_STATE",
    "IMPLEMENTED_DRAWER",
    "IMPLEMENTED_OVERLAY",
    "SYNTHETIC_PREVIEW",
    "DESIGN_ONLY",
]


@dataclass(frozen=True)
class ScreenInfo:
    slug: str
    title: str
    route: str
    status: ScreenStatus
    badge_label: str
    badge_class: str
    spec: str
    notes: str
    is_design_only: bool = False


SCREEN_INVENTORY: dict[str, ScreenInfo] = {
    "dashboard": ScreenInfo(
        slug="dashboard",
        title="Dashboard",
        route="/",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="001, 010, 018",
        notes="One sentence says where the books stand, then what needs you and the open risks. Below, full-width charts grouped by IFRS or US GAAP: money flow, money in and out by month, and the cash-flow statement.",
    ),
    "profit-loss": ScreenInfo(
        slug="profit-loss",
        title="Company profit and loss",
        route="/profit-loss",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="018",
        notes="Accrual management P&L from posted ledger activity, with company account classifications and source rows.",
    ),
    "profit-loss-empty": ScreenInfo(
        slug="profit-loss-empty",
        title="Profit and loss: empty",
        route="/profit-loss",
        status="IMPLEMENTED_STATE",
        badge_label="Implemented state",
        badge_class="badge-low",
        spec="018",
        notes="Accrual management P&L empty state when no transactions or ledger entries are posted.",
    ),
    "profit-loss-partial": ScreenInfo(
        slug="profit-loss-partial",
        title="Profit and loss: partial",
        route="/profit-loss",
        status="IMPLEMENTED_STATE",
        badge_label="Implemented state",
        badge_class="badge-low",
        spec="018",
        notes="Accrual management P&L partial state when some accounts remain unclassified.",
    ),
    "profit-loss-loading": ScreenInfo(
        slug="profit-loss-loading",
        title="Profit and loss: loading",
        route="/profit-loss",
        status="IMPLEMENTED_STATE",
        badge_label="Implemented state",
        badge_class="badge-low",
        spec="018",
        notes="Accrual management P&L loading skeleton state while fetching report figures.",
    ),
    "profit-loss-error": ScreenInfo(
        slug="profit-loss-error",
        title="Profit and loss: error",
        route="/profit-loss",
        status="IMPLEMENTED_STATE",
        badge_label="Implemented state",
        badge_class="badge-low",
        spec="018",
        notes="Accrual management P&L error state when report generation fails.",
    ),
    "profit-loss-entries": ScreenInfo(
        slug="profit-loss-entries",
        title="Profit and loss: source entries",
        route="/profit-loss",
        status="IMPLEMENTED_DRAWER",
        badge_label="Implemented drawer",
        badge_class="badge-low",
        spec="018",
        notes="Slide-out source drawer showing underlying ledger entries for an account classification.",
    ),
    "documents": ScreenInfo(
        slug="documents",
        title="Documents",
        route="/documents",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="003",
        notes="Upload anything in any order. Exact copies are recognised at once; possible copies wait for you; ledgers ask for their columns once.",
    ),
    "document": ScreenInfo(
        slug="document",
        title="Document",
        route="/documents/:docId",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="003, 005, 006",
        notes="One read document: the page viewer with the selected value lit, beside what was read from it, a paginated list with reading marks, its findings and details.",
    ),
    "month": ScreenInfo(
        slug="month",
        title="Month reconciliation",
        route="/months/:month",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="007",
        notes="One month's reconciliation: figures with their provenance marks, the explained risk with next steps, and every bank line with its match and reason.",
    ),
    "reconciliation": ScreenInfo(
        slug="reconciliation",
        title="Bank evidence and document support",
        route="/months/:month",
        status="SYNTHETIC_PREVIEW",
        badge_label="Synthetic preview",
        badge_class="badge-brand",
        spec="007",
        notes="A separate synthetic MYR workspace preview: grouped and split payments, bank-only rows, documents before statements, separate approval/payment confirmation and currency agreement without conversion.",
    ),
    "review": ScreenInfo(
        slug="review",
        title="Review queue",
        route="/review",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="009",
        notes="One queue for everything AI could not settle. Each item shows the evidence, the candidates and only the fixes that make sense.",
    ),
    "evidence-viewer": ScreenInfo(
        slug="evidence-viewer",
        title="Evidence viewer",
        route="In-app overlay (/review, /documents/:id, /months/:m, /risk)",
        status="IMPLEMENTED_OVERLAY",
        badge_label="Implemented overlay",
        badge_class="badge-clean",
        spec="005, 006, 009",
        notes="The lamp on the printed value, the calculation, and both readings side by side. Phones open zoomed to the evidence.",
    ),
    "assistant": ScreenInfo(
        slug="assistant",
        title="Finance Assistant",
        route="/assistant",
        status="IMPLEMENTED",
        badge_label="Implemented (dev runtime)",
        badge_class="badge-clean",
        spec="011",
        notes="Questions about your books, answered from tools with citations and a small chart; only preferences are remembered.",
    ),
    "plan-usage": ScreenInfo(
        slug="plan-usage",
        title="Plan and usage",
        route="/settings/plan",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="013",
        notes="Trial days, usage that warns before a limit, coming-soon plans and features that cannot be clicked.",
    ),
    "onboarding": ScreenInfo(
        slug="onboarding",
        title="Onboarding",
        route="/onboarding",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="001, 013",
        notes="Individual or company in one question; the brand panel explains the promise with a ledger.",
    ),
    "risk": ScreenInfo(
        slug="risk",
        title="Risk",
        route="/risk",
        status="IMPLEMENTED",
        badge_label="Implemented",
        badge_class="badge-clean",
        spec="008",
        notes="Findings grouped by month with their severity and status; each opens the evidence viewer.",
    ),
    "clients": ScreenInfo(
        slug="clients",
        title="Clients and suppliers",
        route="/counterparties",
        status="DESIGN_ONLY",
        badge_label="Design only (P1)",
        badge_class="badge-outline",
        spec="014",
        notes="Clients and suppliers built from the books; a supplier paid to a new account is flagged. Placeholder in current app (spec 014).",
        is_design_only=True,
    ),
    "labels": ScreenInfo(
        slug="labels",
        title="Labels",
        route="/labels",
        status="DESIGN_ONLY",
        badge_label="Design only (P1)",
        badge_class="badge-outline",
        spec="016",
        notes="Every AI decision a person can check, lowest confidence first, with per-page types, extraction files, runs and dataset use. Placeholder in current app (spec 016).",
        is_design_only=True,
    ),
    "runs": ScreenInfo(
        slug="runs",
        title="Runs",
        route="/runs",
        status="DESIGN_ONLY",
        badge_label="Design only (P1)",
        badge_class="badge-outline",
        spec="017",
        notes="Run history like a tracing tool: runs, a span waterfall, and the selected model call with its request, response and label. Placeholder in current app (spec 017).",
        is_design_only=True,
    ),
}
