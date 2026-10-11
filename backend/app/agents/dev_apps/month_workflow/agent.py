"""Development app for interactive debugging of month_workflow in ADK Web UI.

Run `make dev-agents` to inspect the workflow DAG, events, and state in http://localhost:8501.
"""

from datetime import UTC, datetime

from app.agents.deps import PipelineDeps
from app.agents.workflows.month_workflow import build_month_workflow
from app.core.settings import Settings
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.month import Month, MonthState
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository

doc_repo = FakeDocumentRepository()
doc_repo.documents[("org_dev", "stmt_sample_1")] = Document(
    doc_id="stmt_sample_1",
    file_name="bank_statement_2026_03.pdf",
    content_type="application/pdf",
    size_bytes=2048,
    page_count=3,
    sha256="fake_stmt_sha",
    gcs_path="docs/org_dev/stmt_sample_1.pdf",
    uploaded_by="dev_user",
    uploaded_at=datetime(2026, 3, 15, tzinfo=UTC),
    doc_type=DocType.BANK_STATEMENT,
    status=DocStatus.DONE,
    months=["2026-03"],
)

month_repo = FakeMonthRepository()
month_repo.months[("org_dev", "2026-03")] = Month(
    month="2026-03",
    generation=1,
    state=MonthState.COLLECTING,
)

deps = PipelineDeps(
    settings=Settings(),
    run_repo=FakeRunRepository(),
    doc_repo=doc_repo,
    month_repo=month_repo,
)

root_agent = build_month_workflow(deps)
