"""Month workflow node factories with stubs for specs 004-008 (docs/06 §3, §4)."""

from typing import Any

from google.adk import Context

from app.agents.deps import PipelineDeps
from app.agents.stages import stage
from app.domain.models.document import DocStatus, DocType
from app.domain.models.month import Month, MonthState
from app.domain.models.run import RunStatus


def load_month(deps: PipelineDeps):
    @stage(deps, "load_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")

        month_doc = await deps.month_repo.get(org_id, month_str)
        has_statement = bool(month_doc and month_doc.statements)

        if not has_statement:
            docs, _ = await deps.doc_repo.list_documents(
                org_id, month=month_str, doc_type=DocType.BANK_STATEMENT.value
            )
            for d in docs:
                if d.status != DocStatus.FAILED:
                    has_statement = True
                    break

        return {
            **node_input,
            "has_statement": has_statement,
            "summary": "Month data loaded",
        }

    return _node


def reconcile(deps: PipelineDeps):
    @stage(deps, "reconcile")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Reconciliation is not available yet"}

    return _node


def check_month(deps: PipelineDeps):
    @stage(deps, "check_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Month checks completed"}

    return _node


def build_counterparties(deps: PipelineDeps):
    @stage(deps, "build_counterparties")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Counterparties built"}

    return _node


def suggest_profile(deps: PipelineDeps):
    @stage(deps, "suggest_profile")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Profile suggestions completed"}

    return _node


def score_risk(deps: PipelineDeps):
    @stage(deps, "score_risk")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Risk scored"}

    return _node


def explain_month(deps: PipelineDeps):
    @stage(deps, "explain_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Explanation generated"}

    return _node


def build_flows(deps: PipelineDeps):
    @stage(deps, "build_flows")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Money flows built"}

    return _node


def sync_review_items(deps: PipelineDeps):
    @stage(deps, "sync_review_items")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Review items synced"}

    return _node


def finalize_month(deps: PipelineDeps):
    @stage(deps, "finalize_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")
        run_gen = int(node_input.get("generation", 0))
        run_id = str(node_input.get("runId") or node_input.get("run_id") or "")

        current_month = await deps.month_repo.get(org_id, month_str)
        if current_month is not None and current_month.generation > run_gen:
            await deps.run_repo.update_status(org_id, run_id, RunStatus.SUPERSEDED, ended=True)
            return {
                **node_input,
                "status": "SUPERSEDED",
                "skipped": "superseded",
                "summary": "Superseded by newer generation",
            }

        has_statement = bool(node_input.get("has_statement", False))
        # T007-08 will derive this from real results, coverage and blockers. Statement presence
        # alone is not reconciliation; the skeleton must not claim that the books are settled.
        target_state = MonthState.COLLECTING

        if current_month is None:
            current_month = Month(month=month_str, generation=run_gen)
        current_month.state = target_state
        current_month.note = "Reconciliation is not available yet." if has_statement else None
        current_month.dirty = False
        current_month.last_run_id = run_id
        await deps.month_repo.save(org_id, current_month)

        await deps.run_repo.update_status(org_id, run_id, RunStatus.DONE, ended=True)
        return {
            **node_input,
            "status": "DONE",
            "state": target_state.value,
            "summary": f"Month finalized ({target_state.value})",
        }

    return _node
