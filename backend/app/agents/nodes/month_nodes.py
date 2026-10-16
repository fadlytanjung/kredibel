"""Month workflow node factories with stubs for specs 004-008 (docs/06 §3, §4)."""

import hashlib
from dataclasses import replace
from datetime import date
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
from app.domain.accounts import mask_numbers_in_text
from app.domain.candidate_ranking import apply_ranking
from app.domain.categorize import Framework
from app.domain.checks.month import MonthContext, run_month_checks
from app.domain.counterparties import build_counterparties as group_counterparties
from app.domain.evidence import document_evidence, line_support
from app.domain.figures import month_figures
from app.domain.findings import Finding, merge_findings
from app.domain.grounding import GroundingContext, check_grounding
from app.domain.models.document import DocStatus, DocType, DuplicateDecision, DuplicateKind
from app.domain.models.match import StoredMatch
from app.domain.models.month import Month, MonthState
from app.domain.models.run import RunStatus
from app.domain.money_flow import build_money_flow
from app.domain.next_steps import next_steps_for_findings
from app.domain.profile_suggestions import (
    InvoiceFacts,
    StatementFacts,
    build_profile_suggestions,
)
from app.domain.reconcile import assign_matches
from app.domain.review_items import (
    Check,
    HeldCopy,
    HeldEntry,
    LineFacts,
    ProposalFacts,
    RecordFacts,
    ReviewCandidate,
    ReviewItem,
    month_items,
)
from app.domain.risk import RiskAssessment, assess_document_risk, assess_month_risk
from app.services.month_labels import sync_month_labels

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
            ledger_rows=data.ledger_rows,
            bank_account_mappings=data.bank_account_mappings,
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


async def _own_names(deps: PipelineDeps, org_id: str) -> list[str]:
    workspace = await deps.workspaces.get_workspace(org_id) if deps.workspaces else None
    if workspace is None:
        return []
    profile = workspace.profile
    names = [workspace.name, profile.legal_name, profile.trading_name, *profile.aliases]
    return [n for n in names if n]


# Clients and suppliers from every eligible line, invoice and receipt (spec 014, AC-014-1): the
# whole picture is rebuilt by code on each run, so it never depends on the order months ran.
def build_counterparties(deps: PipelineDeps):
    @stage(deps, "build_counterparties")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, month = _org_month(node_input)
        if deps.counterparties is None or deps.categories is None:
            return {**node_input, "summary": "Skipped: counterparty store not configured"}
        data = await read_month(deps, org_id, month)
        if data is None:
            return {**node_input, "summary": "Skipped: the books are not readable"}
        parties = group_counterparties(
            data.all_lines,
            data.invoices,
            data.receipts,
            policy=deps.categories,
            own_names=await _own_names(deps, org_id),
        )
        await deps.counterparties.replace_all(org_id, parties)
        if deps.bank_lines is not None:
            await deps.bank_lines.set_counterparties(
                org_id, {tx: p.counterparty_id for p in parties for tx in p.bank_line_ids}
            )
        if deps.invoices is not None:
            await deps.invoices.set_counterparties(
                org_id, {i: p.counterparty_id for p in parties for i in p.invoice_ids}
            )
        if deps.receipts is not None:
            await deps.receipts.set_counterparties(
                org_id, {r: p.counterparty_id for p in parties for r in p.receipt_ids}
            )
        return {**node_input, "summary": f"{len(parties)} counterpart(ies)"}

    return _node


def _agreed(consensus: dict[str, dict[str, Any]], field: str) -> bool:
    return consensus.get(field, {}).get("status") == "AGREED"


# Profile suggestions from the documents (spec 014, AC-014-4): tax ID and address here; the
# account suggestion is made where the statement is read, with the digits' hash in hand.
def suggest_profile(deps: PipelineDeps):
    @stage(deps, "suggest_profile")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id, _ = _org_month(node_input)
        if deps.suggestions is None or deps.workspaces is None or deps.invoices is None:
            return {**node_input, "summary": "Skipped: suggestion store not configured"}
        workspace = await deps.workspaces.get_workspace(org_id)
        if workspace is None:
            return {**node_input, "summary": "Skipped: no workspace"}
        docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
        statements: list[StatementFacts] = []
        for d in docs:
            meta = d.statement_meta or {}
            if d.doc_type != DocType.BANK_STATEMENT or d.status != DocStatus.DONE or not meta:
                continue
            start = meta.get("periodStart")
            statements.append(
                StatementFacts(
                    doc_id=d.doc_id,
                    page=1,
                    bank_name=meta.get("bankName"),
                    account_masked=meta.get("accountMasked"),
                    account_hash=None,
                    holder_name=meta.get("accountHolder"),
                    holder_address=meta.get("holderAddress"),
                    period_start=date.fromisoformat(start) if start else None,
                    agreed=float((d.reading or {}).get("agreement") or 0) >= 0.99,
                )
            )
        invoices = [
            InvoiceFacts(
                invoice_id=inv.invoice_id,
                doc_id=inv.doc_id,
                page=inv.pages[0] if inv.pages else 1,
                kind=inv.kind,
                issuer_name=inv.issuer_name,
                issuer_tax_id=inv.issuer_tax_id,
                issue_date=inv.issue_date,
                agreed=_agreed(inv.consensus, "issuerTaxId"),
            )
            for inv in await deps.invoices.list_records(org_id, limit=2000)
        ]
        rejected = {
            s.suggestion_id
            for s in await deps.suggestions.list_suggestions(org_id, status="REJECTED")
        }
        fresh = build_profile_suggestions(
            profile=workspace.profile,
            accounts=await deps.workspaces.list_bank_accounts(org_id),
            statements=statements,
            invoices=invoices,
            own_names=await _own_names(deps, org_id),
            rejected=rejected,
        )
        await deps.suggestions.upsert_open(org_id, fresh)
        return {**node_input, "summary": f"{len(fresh)} profile suggestion(s)"}

    return _node


async def _live_month_findings(
    deps: PipelineDeps, pending: PendingMonths | None, node_input: dict[str, Any], month: str
) -> list[Finding]:
    """The month's findings as this run will store them: the stored ones with the run's fresh
    checks merged over them, so the risk and its wording never lag a run behind."""
    assert deps.findings is not None
    org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
    stored = await deps.findings.list_findings(org_id, month=month)
    result = pending.get(run_key(node_input)) if pending is not None else None
    if result is None or result.findings is None:
        return stored
    return merge_findings([f for f in stored if f.scope == "MONTH"], result.findings)


def score_risk(deps: PipelineDeps, pending: PendingMonths | None = None):
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

        month_findings = await _live_month_findings(deps, pending, node_input, month_str)
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


def explain_month(deps: PipelineDeps, pending: PendingMonths | None = None):
    @stage(deps, "explain_month")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month_str = str(node_input.get("month") or "")
        risk_data = node_input.get("risk") or {}
        level = risk_data.get("level", "LOW")

        if deps.findings is None:
            return {**node_input, "summary": "Skipped: findings repo not configured"}

        # 1. Gather all findings (month scoped + document scoped for documents in month)
        month_findings = await _live_month_findings(deps, pending, node_input, month_str)
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

        # 3. Check hash skip (AC-008-6): Gemini's explanation of the same facts is kept; a template
        #    stood in for it and is tried again.
        exp_hash = _compute_explanation_hash(level, unique_findings, figures)
        stored = current_month.risk if current_month and current_month.risk else {}
        if stored.get("hash") == exp_hash and stored.get("grounding") == "VERIFIED":
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
                    "prompt_version": calls[-1].prompt_version,
                    "tokens_in": sum(c.tokens_in for c in calls),
                    "tokens_out": sum(c.tokens_out for c in calls),
                }
                if calls
                else {}
            ),
        }

    return _node


def build_flows(deps: PipelineDeps, pending: PendingMonths | None = None):
    @stage(deps, "build_flows")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        result = pending.get(run_key(node_input)) if pending is not None else None
        if result is None or not node_input.get("computed") or deps.categories is None:
            return {**node_input, "summary": "Skipped: no lines to build flow"}

        workspace = await deps.workspaces.get_workspace(org_id) if deps.workspaces else None
        framework: Framework = (
            workspace.profile.accounting_framework
            if workspace
            and workspace.profile
            and workspace.profile.accounting_framework in ("IFRS", "US_GAAP")
            else "IFRS"
        )
        flow = build_money_flow(
            result.data.lines,
            account_of=result.data.account_of,
            policy=deps.categories,
            framework=framework,
        )
        flows_dict = {
            "links": [
                {
                    "id": link.id,
                    "source": link.source,
                    "target": link.target,
                    "amountMinor": int(link.value * 100),
                    "lineCount": link.line_count,
                }
                for link in flow.links
            ],
            "nodes": [
                {
                    "id": n.id,
                    "column": n.column,
                    "label": n.label,
                    "amountMinor": int(n.value * 100),
                    **({"cashflowClass": n.cashflow_class} if n.cashflow_class else {}),
                    **({"statementLine": n.statement_line} if n.statement_line else {}),
                }
                for n in flow.nodes
            ],
            "framework": framework,
            "totalMinor": int(flow.total * 100),
        }
        return {
            **node_input,
            "flows": flows_dict,
            "summary": f"{len(flow.nodes)} nodes, {len(flow.links)} links",
        }

    return _node


def _checks(consensus: dict[str, dict[str, Any]], fields: tuple[str, ...]) -> tuple[Check, ...]:
    return tuple((f, str(consensus[f].get("status"))) for f in fields if f in consensus)


def sync_review_items(deps: PipelineDeps, pending: PendingMonths | None = None):
    """The month's review items (spec 009, docs/08 §7) from what this run computed; the stores
    still hold the previous run until finalize_month writes."""

    @stage(deps, "sync_review_items")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month = str(node_input.get("month") or "")
        if deps.review_items is None or deps.workspaces is None:
            return {**node_input, "summary": "Skipped: review item sync is not configured"}
        workspace = await deps.workspaces.get_workspace(org_id)
        currency = workspace.currency if workspace else ""
        risk = node_input.get("risk") or {}
        risk_level = str(risk.get("level", "LOW")) if isinstance(risk, dict) else "LOW"
        result = pending.get(run_key(node_input)) if pending is not None else None

        docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
        held_docs = {d.doc_id for d in docs if d.held_as_duplicate}
        held: list[HeldCopy] = []
        for d in docs:
            dup = d.duplicate
            held_copy = dup is not None and dup.kind == DuplicateKind.CONTENT
            if not (held_copy and dup and dup.decision == DuplicateDecision.PENDING):
                continue
            if not d.months or d.months[0] != month:
                continue  # one item per copy, in its first month
            own = (
                await deps.findings.list_findings(org_id, doc_id=d.doc_id) if deps.findings else []
            )
            title = next(
                (f.title for f in own if f.code == dup.code), "This document may be a copy"
            )
            held.append(HeldCopy(d.doc_id, dup.code, dup.of_doc_id, title))

        held_entries: list[HeldEntry] = []
        if deps.ledger is not None:
            names = {d.doc_id: d.file_name for d in docs}
            groups: dict[tuple[str, str, str], list[Any]] = {}
            for row in await deps.ledger.list_rows(org_id):
                dup = row.duplicate or {}
                if not row.held_as_duplicate or dup.get("decision") != "PENDING":
                    continue
                if f"{row.date:%Y-%m}" != month:
                    continue
                reference = " ".join((row.journal_id or "").split())
                groups.setdefault((row.doc_id, row.date.isoformat(), reference), []).append(row)
            for (doc_id, day, reference), rows in sorted(groups.items()):
                rows.sort(key=lambda r: r.row_number)
                when = date.fromisoformat(day)
                held_entries.append(
                    HeldEntry(
                        doc_id=doc_id,
                        entry_ids=tuple(r.entry_id for r in rows),
                        of_entry_ids=tuple((r.duplicate or {}).get("ofEntryId", "") for r in rows),
                        of_doc_id=(rows[0].duplicate or {}).get("ofDocId") or doc_id,
                        title=(
                            f"Ledger entry {reference} of {when.day} {when:%b %Y} appears twice "
                            f"in {names.get(doc_id, doc_id)}"
                        ),
                        key=rows[0].entry_id,
                    )
                )

        cited: dict[str, set[str]] = {}
        if deps.findings is not None:
            for f in await _live_month_findings(deps, pending, node_input, month):
                if f.status == "OPEN":
                    for e in f.evidence:
                        if e.tx_id:
                            cited.setdefault(e.tx_id, set()).add(f.code)
        fresh_support = result.support if result is not None else {}
        fresh_payment: dict[str, dict[str, Any]] = (
            {**result.invoice_evidence, **result.receipt_evidence} if result is not None else {}
        )

        def payment_of(record_id: str, stored: dict[str, Any] | None) -> str | None:
            body = fresh_payment.get(record_id, stored or {})
            return body.get("payment")

        lines = (
            await deps.bank_lines.list_lines(org_id, month=month, limit=5000)
            if deps.bank_lines
            else []
        )
        line_facts = [
            LineFacts(
                ln.tx_id,
                ln.doc_id,
                ln.date,
                ln.amount,
                (fresh_support[ln.tx_id][2] if ln.tx_id in fresh_support else ln.support)
                or "NO_SUPPORT",
                held=ln.doc_id in held_docs,
                checks=_checks(ln.consensus, ("amount", "date")),
                cited_by=tuple(sorted(cited.get(ln.tx_id, ()))),
            )
            for ln in lines
        ]
        day_of = {ln.tx_id: ln.date for ln in lines}

        records: list[RecordFacts] = []
        if deps.invoices:
            for inv in await deps.invoices.list_records(org_id, month=month, limit=2000):
                records.append(
                    RecordFacts(
                        inv.invoice_id,
                        inv.doc_id,
                        "SALES" if inv.kind == "SALES" else "PURCHASE",
                        inv.number,
                        inv.issue_date,
                        inv.total,
                        payment_of(inv.invoice_id, inv.evidence),
                        held=inv.doc_id in held_docs,
                        checks=_checks(inv.consensus, ("total", "issueDate")),
                    )
                )
        if deps.receipts:
            for rc in await deps.receipts.list_records(org_id, month=month, limit=2000):
                records.append(
                    RecordFacts(
                        rc.receipt_id,
                        rc.doc_id,
                        "RECEIPT",
                        rc.number,
                        rc.date,
                        rc.total,
                        payment_of(rc.receipt_id, rc.evidence),
                        held=rc.doc_id in held_docs,
                        checks=_checks(rc.consensus, ("total", "date")),
                    )
                )

        rivals = _rivals(result) if result is not None else {}
        proposals = [
            ProposalFacts(
                m.match_id,
                tuple(m.bank_line_ids),
                tuple(m.invoice_ids),
                tuple(m.receipt_ids),
                m.amount,
                min((day_of[t] for t in m.bank_line_ids if t in day_of), default=None),
                m.score,
                tuple(m.reasons),
                rivals.get(m.match_id, ()),
            )
            for m in (
                [m for m in result.matches if m.status == "PROPOSED"]
                if result is not None
                else await deps.matches.list_matches(org_id, month=month, status="PROPOSED")
                if deps.matches
                else []
            )
        ]

        fresh = month_items(
            month=month,
            currency=currency,
            risk_level=risk_level,
            lines=line_facts,
            records=records,
            proposals=proposals,
            held=held,
            held_entries=held_entries,
        )
        fresh = await rank_proposals(deps, org_id, month, fresh, result)
        written = await deps.review_items.replace_month_review_items(
            org_id, month, fresh, now=deps.clock.now()
        )
        closed = sum(1 for i in written if i.status != "OPEN")
        return {
            **node_input,
            "summary": f"{len(fresh)} open review item(s), {closed} closed",
        }

    return _node


def _rivals(result: MonthResult) -> dict[str, tuple[ReviewCandidate, ...]]:
    """Each proposal's rivals as review candidates, split by the kind of record."""
    invoices = {i.invoice_id for i in result.data.invoices}
    receipts = {r.receipt_id for r in result.data.receipts}
    out: dict[str, tuple[ReviewCandidate, ...]] = {}
    for allocation in result.allocations:
        if not allocation.rivals:
            continue
        out[allocation.match_id] = tuple(
            ReviewCandidate(
                match_id=r.match_id,
                bank_line_ids=[
                    i for i in (*r.left_ids, *r.right_ids) if i not in invoices | receipts
                ],
                invoice_ids=[i for i in (*r.left_ids, *r.right_ids) if i in invoices],
                receipt_ids=[i for i in (*r.left_ids, *r.right_ids) if i in receipts],
                score=r.score,
                reasons=list(r.reasons),
            )
            for r in allocation.rivals
        )
    return out


MAX_RANKED = 8  # proposals the model ranks per month run; the rest wait for the next run


async def rank_proposals(
    deps: PipelineDeps,
    org_id: str,
    month: str,
    items: list[ReviewItem],
    result: MonthResult | None,
) -> list[ReviewItem]:
    # Spec 023, AC-023-7: for a proposal with rivals, the model orders the candidates code found
    # and says why; a ranking is kept while the candidates stay the same. Advice only: the
    # matching, the scores and what is automatic never change; a failed call leaves it unranked.
    if deps.reader is None or result is None or deps.review_items is None:
        return items
    listed, _, _ = await deps.review_items.list_review_items(
        org_id, month=month, kind="PROPOSED_MATCH", limit=500
    )
    stored = {i.item_id: i for i in listed}
    out: list[ReviewItem] = []
    asked = 0
    for item in items:
        candidates = item.suggestion.candidates
        if item.kind != "PROPOSED_MATCH" or len(candidates) < 2:
            out.append(item)
            continue
        before = stored.get(item.item_id)
        same = before is not None and [c.match_id for c in before.suggestion.candidates] == [
            c.match_id for c in candidates
        ]
        if same and before is not None and before.suggestion.ranked_by:
            kept = {c.match_id: c for c in before.suggestion.candidates}
            ranked = [
                replace(c, ai_rank=kept[c.match_id].ai_rank, ai_reason=kept[c.match_id].ai_reason)
                for c in candidates
            ]
            out.append(
                replace(
                    item,
                    suggestion=replace(
                        item.suggestion, candidates=ranked, ranked_by=before.suggestion.ranked_by
                    ),
                )
            )
            continue
        if asked >= MAX_RANKED:
            out.append(item)
            continue
        asked += 1
        try:
            call = await deps.reader.rank_candidates(
                _payment_text(item, result), _candidates_text(candidates, result)
            )
        except Exception:  # noqa: BLE001 - the item stays a plain proposal
            _log.warning("rank_candidates_failed", item_id=item.item_id)
            out.append(item)
            continue
        ranked = apply_ranking(candidates, call.value)
        out.append(
            replace(
                item,
                suggestion=replace(
                    item.suggestion,
                    candidates=ranked,
                    ranked_by=f"{call.model}@{call.prompt_version}",
                ),
            )
        )
    return out


def _payment_text(item: ReviewItem, result: MonthResult) -> str:
    lines = {ln.tx_id: ln for ln in result.data.all_lines}
    rows = [lines[t] for t in item.subject.bank_line_ids if t in lines]
    return "\n".join(
        f"{ln.date.isoformat()} | {mask_numbers_in_text(ln.description)} | {ln.amount}"
        for ln in rows
    )


def _candidates_text(candidates: list[ReviewCandidate], result: MonthResult) -> str:
    invoices = {i.invoice_id: i for i in result.data.invoices}
    receipts = {r.receipt_id: r for r in result.data.receipts}
    out: list[str] = []
    for c in candidates:
        parts = [
            f"invoice {i.number or ''} {_party_of(i)} {i.issue_date} total {i.total}"
            for i in (invoices[x] for x in c.invoice_ids if x in invoices)
        ] + [
            f"receipt {r.number or ''} {r.merchant_name or ''} {r.date} total {r.total}"
            for r in (receipts[x] for x in c.receipt_ids if x in receipts)
        ]
        out.append(
            f"{c.match_id}: {'; '.join(mask_numbers_in_text(p) for p in parts)} "
            f"| code's score {c.score} | reasons {', '.join(c.reasons)}"
        )
    return "\n".join(out)


def _party_of(invoice: Any) -> str:
    return (invoice.issuer_name if invoice.kind == "PURCHASE" else invoice.buyer_name) or ""


def _months_paid_elsewhere(result: MonthResult, month: str) -> set[str]:
    """Months other than this one whose invoices or receipts changed payment evidence."""
    out: set[str] = set()
    for records, fresh in (
        (result.data.invoices, result.invoice_evidence),
        (result.data.receipts, result.receipt_evidence),
    ):
        for record in records:
            record_id = getattr(record, "invoice_id", None) or getattr(record, "receipt_id", "")
            body = fresh.get(record_id)
            if body is None or not record.month or record.month == month:
                continue
            if (record.evidence or {}).get("payment") != body.get("payment"):
                out.add(record.month)
    return out


def sync_labels(deps: PipelineDeps):
    """Spec 016: the month's labels from its finalized books (a category a match or a person
    changed, documents and values read before labels existed); people's decisions win."""

    @stage(deps, "sync_labels")
    async def _node(ctx: Context, node_input: dict[str, Any]) -> dict[str, Any]:
        org_id = str(node_input.get("orgId") or node_input.get("org_id") or "")
        month = str(node_input.get("month") or "")
        if node_input.get("skipped"):
            return {**node_input, "summary": "Skipped: the month run did not finish"}
        if (
            deps.labels is None
            or deps.learning is None
            or deps.categories is None
            or deps.bank_lines is None
        ):
            return {**node_input, "summary": "Skipped: labels are not configured"}
        workspace = await deps.workspaces.get_workspace(org_id) if deps.workspaces else None
        framework = workspace.profile.accounting_framework if workspace else "IFRS"
        written = await sync_month_labels(
            org_id=org_id,
            month=month,
            labels=deps.labels,
            lines=deps.bank_lines,
            documents=deps.doc_repo,
            invoices=deps.invoices,
            receipts=deps.receipts,
            policy=deps.learning,
            categories=deps.categories,
            framework=framework,
            at=deps.clock.now(),
        )
        return {**node_input, "summary": f"{written} labels written"}

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
            paid_elsewhere = _months_paid_elsewhere(result, month_str)  # before the stores change
            await deps.matches.replace_month_matches(org_id, month_str, result.matches)
            await deps.bank_lines.set_support(org_id, result.support)
            await deps.invoices.set_evidence(org_id, result.invoice_evidence)
            await deps.receipts.set_evidence(org_id, result.receipt_evidence)
            if result.findings is not None and deps.findings is not None:
                await deps.findings.replace_month_findings(
                    org_id, month_str, result.findings, run_id=run_id
                )
            # A payment found here settles a document of another month: that month's items and
            # figures follow (docs/08 §7: each run recomputes its own month only).
            for other in sorted(paid_elsewhere):
                if deps.task_queue is None:
                    break
                gen, _ = await deps.month_repo.bump_generation(org_id, other, dirty=True)
                await deps.task_queue.enqueue_month_task(
                    org_id, other, gen, delay_seconds=deps.settings.month_run_delay_seconds
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
        flows_val = node_input.get("flows")
        if isinstance(flows_val, dict):
            current_month.flows = flows_val
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
