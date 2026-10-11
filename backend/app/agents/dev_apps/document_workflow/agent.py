"""Development app for interactive debugging of document_workflow in ADK Web UI.

Run `make dev-agents` to inspect the workflow DAG, events, and state in http://localhost:8501.
"""

from datetime import UTC, datetime

from app.agents.deps import PipelineDeps
from app.agents.workflows.document_workflow import build_document_workflow
from app.core.settings import Settings
from app.domain.models.document import DocStatus, Document
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository

doc_repo = FakeDocumentRepository()
doc_repo.documents[("org_dev", "doc_sample_1")] = Document(
    doc_id="doc_sample_1",
    file_name="sample_statement.pdf",
    content_type="application/pdf",
    size_bytes=1024,
    page_count=2,
    sha256="fake_sha256",
    gcs_path="docs/org_dev/doc_sample_1.pdf",
    uploaded_by="dev_user",
    uploaded_at=datetime(2026, 3, 1, tzinfo=UTC),
    status=DocStatus.UPLOADED,
)

deps = PipelineDeps(
    settings=Settings(),
    run_repo=FakeRunRepository(),
    doc_repo=doc_repo,
    month_repo=FakeMonthRepository(),
)

root_agent = build_document_workflow(deps)
