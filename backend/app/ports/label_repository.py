"""Port: labels and the rules people made from them (spec 016, docs/09 §3.19 and §3.20)."""

from typing import Protocol

from app.domain.examples import Example
from app.domain.labels import Label, WorkspaceRule
from app.domain.models.events import AuditEvent


class LabelRepository(Protocol):
    async def upsert(self, org_id: str, labels: list[Label]) -> list[Label]:
        """Merge each label over the stored one (people win) and return what is stored."""
        ...

    async def get(self, org_id: str, label_id: str) -> Label | None: ...

    async def delete(self, org_id: str, label_ids: list[str]) -> None:
        """Labels that no longer ask anything (spec 016); never one a person decided."""
        ...

    async def list_labels(
        self,
        org_id: str,
        *,
        task: str | None = None,
        status: str | None = None,
        needs_check: bool | None = None,
        doc_id: str | None = None,
        month: str | None = None,
        dataset_use: str | None = None,
        run_id: str | None = None,
        sort: str = "confidence",
        limit: int | None = 50,
    ) -> list[Label]:
        """Lowest confidence first (`confidence`), or newest decision first (`newest`)."""
        ...

    async def decide(self, org_id: str, label: Label, event: AuditEvent) -> None:
        """A person's decision with its audit event, atomically."""
        ...

    async def save_example(
        self, org_id: str, label_id: str, task: str, vector: list[float]
    ) -> None:
        """A decided label's embedding, so it can serve as an example for its task (AC-016-9)."""
        ...

    async def has_examples(self, org_id: str, task: str) -> bool: ...

    async def nearest_examples(
        self, org_id: str, task: str, vector: list[float], limit: int
    ) -> list[Example]:
        """The decided labels of this workspace and task nearest to the vector, best first."""
        ...

    async def save_rule(self, org_id: str, rule: WorkspaceRule) -> None: ...

    async def list_rules(self, org_id: str) -> list[WorkspaceRule]: ...
