"""Month workflow node factories with stubs for specs 004-008 (docs/06 §3, §4)."""

import hashlib
from decimal import Decimal
from typing import Any

import structlog
from google.adk import Context

from app.agents.deps import PipelineDeps
from app.agents.month_data import (
    account_spans,
    allocations_for_checks,
    bank_record,
    confirmations,
    document_facts,
    document_records,
    evidence_body,
    month_bounds,
    person_decisions,
    read_month,
    stored_allocations,
)
from app.agents.month_result import MonthResult, PendingMonths, run_key
from app.agents.stages import stage
from app.domain.checks.month import MonthContext, run_month_checks
from app.domain.evidence import document_evidence, line_support
from app.domain.figures import month_figures
from app.domain.findings import Finding, merge_findings
from app.domain.grounding import GroundingContext, check_grounding
from app.domain.models.document import DocStatus, DocType
from app.domain.models.match import StoredMatch
from app.domain.models.month import Month, MonthState
from app.domain.models.run import RunStatus
from app.domain.next_steps import next_steps_for_findings
from app.domain.reconcile import assign_matches
from app.domain.risk import RiskAssessment, assess_document_risk, assess_month_risk

_log = structlog.get_logger()


def load_month(deps: PipelineDeps):
    @stage(deps, "load_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")

        month_doc = await deps.month_repo.get(org_id, month_str)
        has_statement = bool(month_doc and month_doc.statements)

        if not has_statement:
            # Filtered in memory: the month run must not depend on a composite index.
            docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
            has_statement = any(
                d.doc_type == DocType.BANK_STATEMENT
                and month_str in d.months
                and d.status != DocStatus.FAILED
                for d in docs
            )

        return {
            **node_input,
            "has_statement": has_statement,
            "summary": "Month data loaded",
        }

    return _node


_KIND = {
    "SALES_INVOICE": "BANK_SALES_INVOICE",
    "PURCHASE_INVOICE": "BANK_PURCHASE_INVOICE",
    "RECEIPT": "BANK_RECEIPT",
}


# Reconcile the month from all its data (docs/08 §6, ADR-025): assign matches, store the run's own
# (a person's manual and rejected ones stay), and write payment evidence, bank support and figures.
def reconcile(deps: PipelineDeps, pending: PendingMonths):
    @stage(deps, "reconcile")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, month = _org_month(node_input)
        data = await read_month(deps, org_id, month)
        if data is None:
            return {**node_input, "computed": False, "summary": "Waiting for a statement"}
        assert deps.reconciliation and deps.matches and deps.bank_lines
        assert deps.invoices and deps.receipts and deps.categories
        policy = deps.reconciliation
        left = [bank_record(line, data) for line in data.lines]
        right = document_records(data)
        allocations = assign_matches(
            left, right, policy, workspace_currency=data.currency, decisions=person_decisions(data)
        )
        kinds = {r.record_id: r.kind for r in right}
        amounts = {ln.tx_id: ln.amount for ln in data.all_lines}
        run_id = str(node_input.get("runId") or "")
        now = deps.clock.now()
        stored = [
            StoredMatch(
                match_id=a.match_id,
                month=month,
                kind=_KIND[kinds[a.right_ids[0]]],  # type: ignore[arg-type]
                status=a.status,
                method=a.method,
                bank_line_ids=list(a.left_ids),
                invoice_ids=[r for r in a.right_ids if kinds[r] != "RECEIPT"],
                receipt_ids=[r for r in a.right_ids if kinds[r] == "RECEIPT"],
                amount=sum((abs(amounts.get(t, Decimal(0))) for t in a.left_ids), Decimal(0)),
                amount_difference=a.amount_difference,
                score=a.score,
                reasons=list(a.reasons),
                alternatives=list(a.alternatives),
                requires_review=a.requires_review,
                created_at=now,
                run_id=run_id,
            )
            for a in allocations
            if a.method != "MANUAL"
        ]
        result = MonthResult(data=data, allocations=allocations, matches=stored)
        pending[run_key(node_input)] = result

        # Bank support of the month's lines: separate from cash (ADR-025).
        support: dict[str, tuple[str, list[str], str]] = {}
        for line in data.lines:
            mine = [a for a in allocations if line.tx_id in a.left_ids]
            state = (
                "EXCLUDED"
                if line.cashflow_class == "NON_CASH"
                else (mine[0].method or "PROPOSED")
                if mine
                else "UNMATCHED"
            )
            support[line.tx_id] = (
                state,
                [a.match_id for a in mine],
                line_support(
                    line.tx_id,
                    line.cashflow_class,
                    allocations,
                    not_required=line.tx_id in data.not_required,
                ),
            )
        result.support = support

        # Payment evidence of the documents this month's payments may settle, with every month's
        # stored matches, so a payment found later is seen here too.
        others = stored_allocations([m for m in data.matches if m.month != month])
        everything = [*allocations, *others]
        approved = {d.doc_id for d in data.decisions if d.kind == "DOCUMENT_APPROVAL"}
        first, last = month_bounds(month)
        as_of = now.date()
        for updates, records in (
            (result.invoice_evidence, data.invoices),
            (result.receipt_evidence, data.receipts),
        ):
            for record in records:
                facts = document_facts(record, data)
                if facts is None:
                    continue
                evidence = document_evidence(
                    facts,
                    everything,
                    confirmations(data),
                    account_spans(data),
                    policy,
                    workspace_currency=data.currency,
                    as_of=as_of,
                    bank_amounts=amounts,
                )
                updates[facts.record_id] = evidence_body(evidence, record.doc_id in approved)

        month_invoices = [
            i
            for i in data.invoices
            if i.month == month and (i.currency == data.currency or i.doc_id in data.accepted_docs)
        ]
        month_receipts = [
            r
            for r in data.receipts
            if r.month == month and (r.currency == data.currency or r.doc_id in data.accepted_docs)
        ]
        facts_by_name = month_figures(
            month,
            data.month_lines_by_account(),
            month_invoices,
            month_receipts,
            deps.categories,
            allocations,
        )
        proposals = sum(1 for a in allocations if a.status == "PROPOSED")
        return {
            **node_input,
            "computed": True,
            "has_statement": data.computable,
            "covered": data.covered_whole_month(),
            "proposals": proposals,
            "negativeDays": int(facts_by_name["negative_days"].value),
            "figures": {_camel(n): f.to_dict() for n, f in facts_by_name.items()},
            "statements": [
                {"docId": d.doc_id, "accountMasked": (d.statement_meta or {}).get("accountMasked")}
                for d in data.statements
                if d.doc_id in {s.doc_id for s in data.spans if s.start <= last and s.end >= first}
            ],
            "summary": f"{len(allocations)} matches ({proposals} proposed), "
            f"{sum(1 for v in support.values() if v[2] == 'NO_SUPPORT')} lines without support",
        }

    return _node


def _camel(name: str) -> str:
    if ":" in name:
        return name
    head, *rest = name.split("_")
    return head + "".join(p.title() for p in rest)


def _org_month(node_input: dict[str, Any]) -> tuple[str, str]:
    org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
    return org_id, str(node_input.get("month") or "")


# Month checks (docs/08 §2.2, §2.6, §2.7) over the month's data and its stored matches.
def check_month(deps: PipelineDeps, pending: PendingMonths):
    @stage(deps, "check_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        if not node_input.get("computed") or deps.forensics is None or deps.findings is None:
            return {**node_input, "summary": "Month checks skipped"}
        org_id, month = _org_month(node_input)
        result = pending[run_key(node_input)]
        data = result.data
        assert deps.reconciliation is not None
        context = MonthContext(
            month=month,
            policy=deps.forensics,
            reconciliation=deps.reconciliation,
            workspace_currency=data.currency,
            statements=data.spans,
            lines=data.lines,
            all_lines=data.all_lines,
            invoices=[
                i
                for i in data.invoices
                if i.currency == data.currency or i.doc_id in data.accepted_docs
            ],
            receipts=[
                r
                for r in data.receipts
                if r.currency == data.currency or r.doc_id in data.accepted_docs
            ],
            allocations=allocations_for_checks(result.allocations, data.matches, month),
            negative_days=int(node_input.get("negativeDays") or 0),
        )
        fresh = run_month_checks(context)
        result.findings = fresh
        existing = await deps.findings.list_findings(org_id, month=month, limit=1000)
        stored = merge_findings([f for f in existing if f.scope == "MONTH"], fresh)
        # A statement's own integrity findings block an unqualified completion too (ADR-025).
        first, last = month_bounds(month)
        for span in data.spans:
            if span.start <= last and span.end >= first:
                stored += await deps.findings.list_findings(org_id, doc_id=span.doc_id)
        live = [f for f in stored if f.status in ("OPEN", "ACKNOWLEDGED")]
        blocking = sum(1 for f in live if f.severity in ("CRITICAL", "HIGH"))
        return {
            **node_input,
            "blockingFindings": blocking,
            "summary": f"{len(fresh)} month finding(s), {blocking} blocking",
        }

    return _node


def build_counterparties(deps: PipelineDeps):
    @stage(deps, "build_counterparties")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Skipped: counterparty building is not implemented"}

    return _node


def suggest_profile(deps: PipelineDeps):
    @stage(deps, "suggest_profile")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Skipped: profile suggestions are not implemented"}

    return _node


def score_risk(deps: PipelineDeps):
    @stage(deps, "score_risk")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")

        if deps.risk_policy is None or deps.findings is None:
            return {**node_input, "summary": "Skipped: risk policy or findings repo not configured"}

        docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
        month_docs = [d for d in docs if month_str in d.months and d.status != DocStatus.FAILED]

        doc_assessments: list[RiskAssessment] = []
        for d in month_docs:
            if d.risk and "level" in d.risk:
                doc_assessments.append(
                    RiskAssessment(
                        level=d.risk["level"],
                        score=int(d.risk.get("score", 0)),
                        reasons=tuple(d.risk.get("reasons", ())),
                    )
                )
            elif d.integrity:
                d_findings = await deps.findings.list_findings(org_id, doc_id=d.doc_id)
                v = d.integrity.get("verdict")
                doc_assessments.append(assess_document_risk(v, d_findings, deps.risk_policy))

        month_findings = await deps.findings.list_findings(org_id, month=month_str)
        m_risk = assess_month_risk(doc_assessments, month_findings, deps.risk_policy)

        risk_data = {
            "level": m_risk.level,
            "score": m_risk.score,
            "reasons": list(m_risk.reasons),
        }
        return {
            **node_input,
            "risk": risk_data,
            "summary": f"Month risk: {m_risk.level} ({m_risk.score})",
        }

    return _node


def _compute_explanation_hash(level: str, findings: list[Finding], figures: dict[str, Any]) -> str:
    components = [
        level,
        ",".join(sorted(f"{f.finding_id}:{f.status}" for f in findings)),
        ",".join(
            sorted(f"{k}:{v}" for k, v in figures.items() if isinstance(v, (str, int, float)))
        ),
    ]
    return hashlib.sha256("|".join(components).encode("utf-8")).hexdigest()


def explain_month(deps: PipelineDeps):
    @stage(deps, "explain_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")
        risk_data = node_input.get("risk") or {}
        level = risk_data.get("level", "LOW")

        if deps.findings is None:
            return {**node_input, "summary": "Skipped: findings repo not configured"}

        # 1. Gather all findings (month scoped + document scoped for documents in month)
        month_findings = await deps.findings.list_findings(org_id, month=month_str)
        docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
        month_docs = [d for d in docs if month_str in d.months and d.status != DocStatus.FAILED]
        all_findings_list: list[Finding] = list(month_findings)
        for doc in month_docs:
            d_findings = await deps.findings.list_findings(org_id, doc_id=doc.doc_id)
            all_findings_list.extend(d_findings)

        unique_findings_map = {f.finding_id: f for f in all_findings_list}
        unique_findings = list(unique_findings_map.values())
        live_findings = [f for f in unique_findings if f.status in ("OPEN", "ACKNOWLEDGED")]

        # 2. Extract facts and figures
        current_month = await deps.month_repo.get(org_id, month_str)
        figures = (
            node_input.get("figures") or (current_month.figures if current_month else {}) or {}
        )

        # 3. Check hash skip (AC-008-6)
        exp_hash = _compute_explanation_hash(level, unique_findings, figures)
        if current_month and current_month.risk and current_month.risk.get("hash") == exp_hash:
            return {
                **node_input,
                "summary": "Explanation unchanged (hash skip)",
            }

        # 4. Determine catalog next steps (AC-008-4)
        catalog_steps = (
            next_steps_for_findings(live_findings, deps.risk_policy) if deps.risk_policy else []
        )

        # 5. Build grounding context
        facts_dict: dict[str, Any] = {}
        for k, v in figures.items():
            if isinstance(v, dict) and "value" in v:
                facts_dict[f"{month_str}:{k}"] = v["value"]
                facts_dict[k] = v["value"]
            elif isinstance(v, (str, int, float, Decimal)):
                facts_dict[f"{month_str}:{k}"] = v
                facts_dict[k] = v

        grounding_ctx = GroundingContext(
            facts=facts_dict,
            findings=unique_findings_map,
            documents={d.doc_id for d in month_docs},
        )

        # 6. Call reader / explainer if reader available
        summary: str = ""
        ordered_steps: list[str] = list(catalog_steps)
        finding_explanations: dict[str, str] = {}
        grounding = "TEMPLATE"
        fallback = "no reader"
        calls: list[Any] = []  # every model call, recorded on the run's stage

        if deps.reader:
            try:
                findings_text = "\n".join(
                    f"- {f.finding_id} ({f.code}, {f.severity}): {f.title}. Facts: {f.facts}"
                    for f in live_findings
                )
                figures_text = "\n".join(f"- {k}: {v}" for k, v in facts_dict.items())

                res = await deps.reader.explain_month(
                    level=level,
                    findings_facts=findings_text,
                    figures_summary=figures_text,
                    catalog_steps=catalog_steps,
                )
                calls.append(res)
                explanation_val = res.value
                g_res = check_grounding(explanation_val.summary, grounding_ctx)

                if g_res.valid:
                    grounding = "VERIFIED"
                    summary = explanation_val.summary
                    ordered_steps = explanation_val.next_steps or catalog_steps
                    finding_explanations = {
                        fe.finding_id: fe.explanation for fe in explanation_val.finding_explanations
                    }
                else:
                    # Retry once with problems appended (AC-008-5)
                    retry_res = await deps.reader.explain_month(
                        level=level,
                        findings_facts=findings_text,
                        figures_summary=figures_text,
                        catalog_steps=catalog_steps,
                        retry_problems=g_res.problems,
                    )
                    calls.append(retry_res)
                    retry_val = retry_res.value
                    retry_g_res = check_grounding(retry_val.summary, grounding_ctx)
                    if retry_g_res.valid:
                        grounding = "VERIFIED"
                        summary = retry_val.summary
                        ordered_steps = retry_val.next_steps or catalog_steps
                        finding_explanations = {
                            fe.finding_id: fe.explanation for fe in retry_val.finding_explanations
                        }
                    else:
                        fallback = "not grounded"
            except Exception as error:  # noqa: BLE001 - the template stands in; the run says why
                grounding = "TEMPLATE"
                fallback = type(error).__name__
            if grounding == "TEMPLATE":
                # Counts only: the problems quote the model's sentences, which name parties.
                _log.warning("explain_month.template", reason=fallback, calls=len(calls))

        # 7. Template fallback if not verified
        if grounding == "TEMPLATE" or not summary:
            grounding = "TEMPLATE"
            if level == "CRITICAL":
                summary = (
                    "Critical fraud risk detected for this month based on document integrity "
                    "and arithmetic findings."
                )
            elif level == "HIGH":
                summary = (
                    "High fraud risk detected for this month requiring verification "
                    "before sign-off."
                )
            elif level == "MEDIUM":
                summary = (
                    "Medium risk items or held possible duplicates require review before closing."
                )
            else:
                summary = "No high-risk findings detected for this month."
            ordered_steps = catalog_steps
            finding_explanations = {
                f.finding_id: f.title for f in live_findings if f.severity in ("HIGH", "CRITICAL")
            }

        # 8. Update month findings in finding_repo with their explanation if present
        if finding_explanations and month_findings:
            updated_month_findings = []
            for f in month_findings:
                if f.finding_id in finding_explanations:
                    f.explanation = finding_explanations[f.finding_id]
                updated_month_findings.append(f)
            run_id = str(node_input.get("runId") or node_input.get("run_id") or "")
            await deps.findings.replace_month_findings(
                org_id, month_str, updated_month_findings, run_id=run_id
            )

        # 9. Store in risk_data
        updated_risk = {
            **risk_data,
            "summary": summary,
            "nextSteps": ordered_steps,
            "findingExplanations": finding_explanations,
            "grounding": grounding,
            "hash": exp_hash,
        }

        outcome = grounding if grounding == "VERIFIED" else f"TEMPLATE: {fallback}"
        return {
            **node_input,
            "risk": updated_risk,
            "summary": f"Month explanation generated ({outcome})",
            **(
                {
                    "model": calls[-1].model,
                    "tokens_in": sum(c.tokens_in for c in calls),
                    "tokens_out": sum(c.tokens_out for c in calls),
                }
                if calls
                else {}
            ),
        }

    return _node


def build_flows(deps: PipelineDeps):
    @stage(deps, "build_flows")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Skipped: money flows are not implemented"}

    return _node


def sync_review_items(deps: PipelineDeps):
    @stage(deps, "sync_review_items")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        return {**node_input, "summary": "Skipped: review item sync is not implemented"}

    return _node


def finalize_month(deps: PipelineDeps, pending: PendingMonths):
    @stage(deps, "finalize_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")
        run_gen = int(node_input.get("generation", 0))
        run_id = str(node_input.get("runId") or node_input.get("run_id") or "")

        current_month = await deps.month_repo.get(org_id, month_str)
        result = pending.pop(run_key(node_input), None)
        if current_month is not None and current_month.generation > run_gen:
            await deps.run_repo.update_status(org_id, run_id, RunStatus.SUPERSEDED, ended=True)
            return {
                **node_input,
                "status": "SUPERSEDED",
                "skipped": "superseded",
                "summary": "Superseded by newer generation",
            }

        if result is not None:
            assert deps.matches and deps.bank_lines and deps.invoices and deps.receipts
            await deps.matches.replace_month_matches(org_id, month_str, result.matches)
            await deps.bank_lines.set_support(org_id, result.support)
            await deps.invoices.set_evidence(org_id, result.invoice_evidence)
            await deps.receipts.set_evidence(org_id, result.receipt_evidence)
            if result.findings is not None and deps.findings is not None:
                await deps.findings.replace_month_findings(
                    org_id, month_str, result.findings, run_id=run_id
                )

        has_statement = bool(node_input.get("has_statement", False))
        target_state, note = _month_state(node_input, has_statement)

        if current_month is None:
            current_month = Month(month=month_str, generation=run_gen)
        current_month.state = target_state
        current_month.note = note
        if node_input.get("computed"):
            current_month.figures = node_input.get("figures") or {}
            current_month.statements = node_input.get("statements") or []
        risk_val = node_input.get("risk")
        if isinstance(risk_val, dict):
            current_month.risk = risk_val
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


def _month_state(node_input: dict[str, Any], has_statement: bool) -> tuple[MonthState, str | None]:
    """RECONCILED only after real computation over statements covering the whole month, with no
    proposals waiting and no blocking finding; a statement alone is never enough (ADR-025)."""
    if not node_input.get("computed"):
        return (
            MonthState.COLLECTING,
            "Reconciliation is not available yet." if has_statement else None,
        )
    if not node_input.get("covered"):
        return MonthState.COLLECTING, (
            "Statements cover only part of this month."
            if has_statement
            else "Waiting for a bank statement."
        )
    if int(node_input.get("proposals") or 0) or int(node_input.get("blockingFindings") or 0):
        return MonthState.NEEDS_REVIEW, None
    return MonthState.RECONCILED, None
