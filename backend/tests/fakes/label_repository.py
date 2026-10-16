"""In-memory labels and workspace rules for tests."""

from app.domain.examples import Example, cosine
from app.domain.labels import Label, WorkspaceRule, merge
from app.domain.models.events import AuditEvent
from app.ports.label_repository import LabelRepository


def _confidence(label: Label) -> float:
    return float(label.ai.confidence) if label.ai.confidence is not None else -1.0


class FakeLabelRepository(LabelRepository):
    def __init__(self) -> None:
        self.labels: dict[tuple[str, str], Label] = {}
        self.rules: dict[tuple[str, str], WorkspaceRule] = {}
        self.events: list[AuditEvent] = []
        self.vectors: dict[tuple[str, str], tuple[str, list[float]]] = {}

    async def upsert(self, org_id: str, labels: list[Label]) -> list[Label]:
        out = []
        for fresh in labels:
            key = (org_id, fresh.label_id)
            stored = merge(self.labels.get(key), fresh)
            self.labels[key] = stored
            out.append(stored)
        return out

    async def get(self, org_id: str, label_id: str) -> Label | None:
        return self.labels.get((org_id, label_id))

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
        found = [
            lb
            for (o, _), lb in self.labels.items()
            if o == org_id
            and (task is None or lb.task == task)
            and (status is None or lb.status == status)
            and (needs_check is None or lb.needs_check == needs_check)
            and (doc_id is None or lb.subject.doc_id == doc_id)
            and (month is None or lb.month == month)
            and (dataset_use is None or lb.dataset_use == dataset_use)
            and (run_id is None or lb.ai.run_id == run_id)
        ]
        if sort == "newest":
            found.sort(key=lambda lb: (lb.decided_at or lb.ai.at).isoformat(), reverse=True)
        else:
            found.sort(key=lambda lb: (not lb.needs_check, _confidence(lb), lb.label_id))
        return found if limit is None else found[:limit]

    async def decide(self, org_id: str, label: Label, event: AuditEvent) -> None:
        self.labels[(org_id, label.label_id)] = label
        self.events.append(event)

    async def save_example(
        self, org_id: str, label_id: str, task: str, vector: list[float]
    ) -> None:
        self.vectors[(org_id, label_id)] = (task, list(vector))

    async def has_examples(self, org_id: str, task: str) -> bool:
        return any(o == org_id and t == task for (o, _), (t, _) in self.vectors.items())

    async def nearest_examples(
        self, org_id: str, task: str, vector: list[float], limit: int
    ) -> list[Example]:
        found = []
        for (o, label_id), (t, v) in self.vectors.items():
            label = self.labels.get((o, label_id))
            if o != org_id or t != task or label is None:
                continue
            found.append(
                Example(
                    o, label_id, t, label.example_text or "", label.final_value, cosine(vector, v)
                )
            )
        found.sort(key=lambda e: (-e.similarity, e.label_id))
        return found[:limit]

    async def save_rule(self, org_id: str, rule: WorkspaceRule) -> None:
        self.rules[(org_id, rule.rule_id)] = rule

    async def list_rules(self, org_id: str) -> list[WorkspaceRule]:
        return [r for (o, _), r in self.rules.items() if o == org_id and r.active]
