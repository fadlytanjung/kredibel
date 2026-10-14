"""What routers need from the composition root, as a Protocol so api/ never imports adapters."""

from typing import Protocol

from app.core.auth import Principal
from app.core.clock import Clock
from app.domain.plans import PlanCatalog
from app.ports.finding_repository import FindingRepository
from app.ports.match_repository import MatchRepository
from app.services.assistant_service import AssistantService
from app.services.bank_line_service import BankLineService
from app.services.decision_service import DecisionService
from app.services.document_service import DocumentService
from app.services.entitlement_service import EntitlementService
from app.services.finding_service import FindingService
from app.services.insight_service import InsightService
from app.services.match_service import MatchService
from app.services.month_service import MonthService
from app.services.profit_loss_service import ProfitLossService
from app.services.record_service import RecordService
from app.services.review_service import ReviewService
from app.services.runs import RunService
from app.services.workspace_service import WorkspaceService


class ServiceProvider(Protocol):
    @property
    def profit_loss_service(self) -> ProfitLossService: ...

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

    @property
    def insight_service(self) -> InsightService: ...

    @property
    def record_service(self) -> RecordService: ...

    @property
    def findings(self) -> FindingRepository: ...

    @property
    def matches(self) -> MatchRepository: ...

    @property
    def decision_service(self) -> DecisionService: ...

    @property
    def match_service(self) -> MatchService: ...

    @property
    def finding_service(self) -> FindingService: ...

    @property
    def review_service(self) -> ReviewService: ...

    @property
    def assistant_service(self) -> AssistantService: ...


def org_of(principal: Principal) -> str:
    """The workspace of a principal that passed require_workspace."""
    assert principal.org_id is not None
    return principal.org_id
