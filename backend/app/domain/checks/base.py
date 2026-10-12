"""What a document check sees and how checks are registered (docs/08 §1). Pure."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from app.domain.findings import Category, Evidence, Finding, Severity, finding_id
from app.domain.models.bank_line import BankLine
from app.domain.models.document import Document
from app.domain.models.invoice import Invoice, Receipt

from .policy import ForensicsPolicy


@dataclass(frozen=True)
class ValueFont:
    """An amount-like word with the font it is drawn in (for M04)."""

    page: int
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    font: str
    size: float


@dataclass(frozen=True)
class PdfInfo:
    """What inspecting the original file found (docs/07 §3.3); stored on the document as `pdf`."""

    producer: str | None = None
    creator: str | None = None
    created: datetime | None = None
    modified: datetime | None = None
    revisions: int = 1  # saves of the file; a linearized file's first-page section is not one
    revision_changes: tuple[str, ...] = ()  # per later save: CONTENT, SIGNATURE, ANNOTATION, OTHER
    value_fonts: tuple[ValueFont, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "producer": self.producer,
            "creator": self.creator,
            "created": self.created.isoformat() if self.created else None,
            "modified": self.modified.isoformat() if self.modified else None,
            "revisions": self.revisions,
            "revisionChanges": list(self.revision_changes),
            "valueFonts": [
                [v.page, v.text, v.x0, v.x1, v.top, v.bottom, v.font, v.size]
                for v in self.value_fonts
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PdfInfo | None":
        if not data:
            return None

        def when(v: Any) -> datetime | None:
            return datetime.fromisoformat(v) if v else None

        return cls(
            producer=data.get("producer"),
            creator=data.get("creator"),
            created=when(data.get("created")),
            modified=when(data.get("modified")),
            revisions=int(data.get("revisions") or 1),
            revision_changes=tuple(data.get("revisionChanges") or ()),
            value_fonts=tuple(
                ValueFont(
                    page=int(v[0]),
                    text=str(v[1]),
                    x0=float(v[2]),
                    x1=float(v[3]),
                    top=float(v[4]),
                    bottom=float(v[5]),
                    font=str(v[6]),
                    size=float(v[7]),
                )
                for v in data.get("valueFonts") or ()
            ),
        )


@dataclass
class DeclaredAccount:
    bank_name: str
    account_masked: str
    holder_name: str


@dataclass
class CheckContext:
    doc: Document
    policy: ForensicsPolicy
    pdf: PdfInfo | None = None
    lines: list[BankLine] = field(default_factory=list)
    opening: Decimal | None = None
    closing: Decimal | None = None
    invoices: list[Invoice] = field(default_factory=list)
    receipts: list[Receipt] = field(default_factory=list)
    own_names: list[str] = field(default_factory=list)
    accounts: list[DeclaredAccount] = field(default_factory=list)

    @property
    def doc_id(self) -> str:
        return self.doc.doc_id

    def finding(
        self,
        code: str,
        anchor: str,
        *,
        category: Category,
        severity: Severity,
        title: str,
        facts: dict[str, str],
        evidence: list[Evidence],
        month: str | None = None,
    ) -> Finding:
        return Finding(
            finding_id=finding_id(code, f"{self.doc_id}|{anchor}"),
            code=code,
            category=category,
            severity=severity,
            title=title,
            facts=facts,
            evidence=evidence,
            doc_id=self.doc_id,
            month=month,
            next_steps=[s] if (s := self.policy.next_steps.get(code)) else [],
        )


CheckFn = Callable[[CheckContext], list[Finding]]


@dataclass(frozen=True)
class Check:
    code: str
    scope: Literal["DOCUMENT", "MONTH"]
    run: CheckFn


REGISTRY: dict[str, Check] = {}


def check(
    code: str, scope: Literal["DOCUMENT", "MONTH"] = "DOCUMENT"
) -> Callable[[CheckFn], CheckFn]:
    """Register a check under its code; it runs only when the policy enables that code."""

    def register(fn: CheckFn) -> CheckFn:
        REGISTRY[code] = Check(code, scope, fn)
        return fn

    return register


def run_document_checks(ctx: CheckContext) -> list[Finding]:
    from . import arithmetic, extraction, holder, structure  # noqa: F401  (registers the checks)

    out: list[Finding] = []
    for code, registered in sorted(REGISTRY.items()):
        if registered.scope == "DOCUMENT" and code in ctx.policy.enabled:
            out += registered.run(ctx)
    return out
