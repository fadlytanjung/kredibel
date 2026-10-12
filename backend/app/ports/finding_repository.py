"""Findings (docs/09 §3.12), replaced per document by the re-run rules of docs/08 §1."""

from typing import Protocol

from app.domain.findings import Finding


class FindingRepository(Protocol):
    async def replace_document_findings(
        self,
        org_id: str,
        doc_id: str,
        fresh: list[Finding],
        *,
        run_id: str | None,
        categories: set[str] | None = None,
    ) -> list[Finding]:
        """Merge a run's findings over the stored ones of these categories (all when None), so the
        checks and the duplicate detection never resolve each other's findings."""
        ...

    async def list_findings(
        self,
        org_id: str,
        *,
        doc_id: str | None = None,
        month: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Finding]:
        """Most severe first."""
        ...

    async def replace_month_findings(
        self, org_id: str, month: str, fresh: list[Finding], *, run_id: str | None
    ) -> list[Finding]:
        """Merge a month run's MONTH-scope findings over the stored ones of that month."""
        ...

    async def get_finding(self, org_id: str, finding_id: str) -> Finding | None:
        """Fetch a single finding by ID in the workspace. Returns None if foreign or missing."""
        ...

    async def save_finding(self, org_id: str, finding: Finding) -> None:
        """Save an updated finding in the workspace."""
        ...

