"""What routers need from the composition root, as a Protocol so api/ never imports adapters."""

from typing import Protocol

from app.core.auth import Principal
from app.core.clock import Clock
from app.domain.plans import PlanCatalog
from app.services.bank_line_service import BankLineService
from app.services.document_service import DocumentService
from app.services.entitlement_service import EntitlementService
from app.services.month_service import MonthService
from app.services.runs import RunService
from app.services.workspace_service import WorkspaceService


class ServiceProvider(Protocol):
    @property
    def plans(self) -> PlanCatalog: ...

    @property
    def clock(self) -> Clock: ...

    @property
    def workspace_service(self) -> WorkspaceService: ...

    @property
    def entitlement_service(self) -> EntitlementService: ...

    @property
    def document_service(self) -> DocumentService: ...

    @property
    def run_service(self) -> RunService: ...

    @property
    def month_service(self) -> MonthService: ...

    @property
    def bank_line_service(self) -> BankLineService: ...


def org_of(principal: Principal) -> str:
    """The workspace of a principal that passed require_workspace."""
    assert principal.org_id is not None
    return principal.org_id
