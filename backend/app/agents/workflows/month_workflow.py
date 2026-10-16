"""Month workflow static graph (AC-004-5, AC-004-7, docs/06 §3)."""

from google.adk import Workflow

from app.agents.deps import PipelineDeps
from app.agents.month_result import PendingMonths
from app.agents.nodes import month_nodes as m


def build_month_workflow(deps: PipelineDeps) -> Workflow:
    """Build static ADK month_workflow graph with stub or real nodes."""
    load_month = m.load_month(deps)
    pending: PendingMonths = {}
    reconcile = m.reconcile(deps, pending)
    check_month = m.check_month(deps, pending)
    build_counterparties = m.build_counterparties(deps)
    suggest_profile = m.suggest_profile(deps)
    score_risk = m.score_risk(deps, pending)
    explain_month = m.explain_month(deps, pending)
    build_flows = m.build_flows(deps, pending)
    sync_review_items = m.sync_review_items(deps, pending)
    finalize_month = m.finalize_month(deps, pending)
    sync_labels = m.sync_labels(deps)

    return Workflow(
        name="month_workflow",
        edges=[
            ("START", load_month),
            (load_month, reconcile),
            (reconcile, check_month),
            (check_month, build_counterparties),
            (build_counterparties, suggest_profile),
            (suggest_profile, score_risk),
            (score_risk, explain_month),
            (explain_month, build_flows),
            (build_flows, sync_review_items),
            (sync_review_items, finalize_month),
            (finalize_month, sync_labels),
        ],
    )
