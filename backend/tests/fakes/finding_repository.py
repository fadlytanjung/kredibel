"""In-memory findings for tests."""

from app.domain.findings import Finding, merge_findings
from app.ports.finding_repository import FindingRepository


class FakeFindingRepository(FindingRepository):
    def __init__(self) -> None:
        self.findings: dict[tuple[str, str], Finding] = {}

    async def replace_document_findings(
        self,
        org_id: str,
        doc_id: str,
        fresh: list[Finding],
        *,
        run_id: str | None,
        categories: set[str] | None = None,
    ) -> list[Finding]:
        existing = [
            f
            for f in await self.list_findings(org_id, doc_id=doc_id, limit=1000)
            if categories is None or f.category in categories
        ]
        for f in fresh:
            f.last_seen_run_id = run_id
        merged = merge_findings(existing, fresh)
        for f in merged:
            self.findings[(org_id, f.finding_id)] = f
        return merged

    async def replace_month_findings(
        self, org_id: str, month: str, fresh: list[Finding], *, run_id: str | None
    ) -> list[Finding]:
        existing = [
            f
            for f in await self.list_findings(org_id, month=month, limit=1000)
            if f.scope == "MONTH"
        ]
        for f in fresh:
            f.last_seen_run_id = run_id
        merged = merge_findings(existing, fresh)
        for f in merged:
            self.findings[(org_id, f.finding_id)] = f
        return merged

    async def list_findings(
        self,
        org_id: str,
        *,
        doc_id: str | None = None,
        month: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Finding]:
        found = [
            f
            for (o, _), f in self.findings.items()
            if o == org_id
            and (doc_id is None or f.doc_id == doc_id)
            and (month is None or f.month == month)
            and (status is None or f.status == status)
        ]
        return sorted(found, key=lambda f: (f.severity_rank, f.code, f.finding_id))[:limit]

    async def get_finding(self, org_id: str, finding_id: str) -> Finding | None:
        return self.findings.get((org_id, finding_id))

    async def save_finding(self, org_id: str, finding: Finding) -> None:
        self.findings[(org_id, finding.finding_id)] = finding
