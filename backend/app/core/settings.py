"""Application configuration and environment variable validation.

Normative reference: docs/16-infrastructure-and-deployment.md §6.1.
"""

from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppRole = Literal["web", "worker", "all", "migrate"]


class Settings(BaseSettings):
    """Kredibel application settings validated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_role: AppRole = "all"
    app_version: str = "dev"
    # Set by Cloud Run on every service (kredibel-web, kredibel-worker); used as the log `service`.
    k_service: str | None = None
    log_level: str = "INFO"
    data_class: Literal["synthetic", "real"] = "synthetic"
    signup_mode: Literal["open", "invite_only", "closed"] = "open"
    max_workspaces: int = 15
    runs_enabled: bool = True
    run_quota_per_org_per_day: int = 80

    # Google Cloud Platform
    google_cloud_project: str = "cloud-hack2skill"
    google_cloud_location: str = "global"
    google_genai_use_vertexai: bool = True
    region: str = "asia-southeast1"

    # Cloud Storage
    docs_bucket: str = "cloud-hack2skill-kredibel-docs"
    backups_bucket: str = "cloud-hack2skill-kredibel-backups"
    agent_content_bucket: str = "cloud-hack2skill-kredibel-agent-content"

    # Firestore emulator
    firestore_emulator_host: str | None = None

    # Task Queues
    task_queue_mode: Literal["cloud", "inline"] = "inline"
    tasks_location: str = "asia-southeast1"
    tasks_queue_documents: str = "kredibel-documents"
    tasks_queue_months: str = "kredibel-months"
    month_run_delay_seconds: int = 20
    worker_url: str = "http://localhost:8000"
    tasks_invoker_sa: str = "kredibel-tasks-invoker@cloud-hack2skill.iam.gserviceaccount.com"

    # Document AI Processors
    docai_location: str = "us"
    docai_ocr_processor_id: str = ""
    docai_ocr_version: str = ""
    docai_form_processor_id: str = ""
    docai_form_version: str = ""
    docai_invoice_processor_id: str = ""
    docai_invoice_version: str = ""

    # Extraction parameters
    extraction_mode: Literal["adaptive", "thorough"] = "adaptive"
    extraction_escalation: Literal["off", "on"] = "off"
    escalation_max_pages_per_month: int = 30
    read_media_resolution: Literal["high", "ultra_high"] = "high"
    page_concurrency: int = 6
    extraction_cache: Literal["on", "ocr_only", "off"] = "on"
    prefill_on_upload: Literal["off", "on"] = "off"
    explainer_max_attempts: int = 2
    document_run_budget_seconds: int = 600
    month_run_budget_seconds: int = 120

    # Models (Active Gemini 3.8 / Latest)
    model_fast: str = "gemini-3.8-flash"
    model_lite: str = "gemini-flash-lite-latest"
    model_embedding: str = "gemini-embedding-001"
    eval_judge_model: str = "gemini-3.8-flash"
    gemini_api_key: str | None = None

    # Model Armor (P1)
    model_armor_location: str = "asia-southeast1"
    model_armor_template: str = "kredibel-docs"

    # Assistant Memory & Sessions (P1)
    memory_bank_id: str = ""
    agent_sessions_id: str = ""
    assistant_location: str = "asia-southeast1"
    assistant_memory: Literal["on", "off"] = "off"

    # Policy & Contracts
    plans_file: str = "contracts/plans.v1.yaml"
    policy_dir: str = "contracts/policy"
    categories_file: str = "contracts/policy/categories.v1.yaml"
    learning_file: str = "contracts/policy/learning.v1.yaml"

    # Observability
    ai_content_capture: Literal["off", "synthetic"] = "off"
    adk_capture_message_content_in_spans: bool = False
    analytics_dataset: str = "kredibel_agent_analytics"

    # Migrations
    migration_max_ops_per_sec: int = 500
    migration_page_size: int = 300
    migration_export_before_run: bool = False

    # Feature flags
    feature_model_armor: bool = False
    feature_visual_forensics: bool = False
    feature_revision_diff: bool = False
    feature_assistant: bool = False
    feature_roles: bool = False
    feature_run_graph: bool = False
    feature_sign_off: bool = False
    feature_labels: bool = False
    feature_agent_analytics: bool = False
    feature_dataset_export: bool = False

    @model_validator(mode="after")
    def _content_capture_only_on_synthetic_data(self) -> Self:
        # Non-negotiable 17: prompts and responses are recorded only with synthetic data.
        if self.ai_content_capture == "synthetic" and self.data_class != "synthetic":
            raise ValueError("AI_CONTENT_CAPTURE=synthetic requires DATA_CLASS=synthetic")
        return self

    @property
    def capture_span_content(self) -> bool:
        """ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS as start-up sets it: on only when synthetic."""
        return self.ai_content_capture == "synthetic"

    @property
    def service_name(self) -> str:
        """Name in every log line: the Cloud Run service, or kredibel-<role> elsewhere."""
        return self.k_service or f"kredibel-{self.app_role}"
