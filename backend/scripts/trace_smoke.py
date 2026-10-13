"""No Google credentials or workspace access: prove local OTLP export and ingestion, in Jaeger
(default) or, with --langfuse, in the local Langfuse (ADR-026; keys from the environment, which
`make langfuse-smoke` reads from infra/langfuse/.env)."""

import base64
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.core.settings import Settings
from app.observability.tracing import setup_tracing


def langfuse() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        trace_export="langfuse",
        data_class="synthetic",
        ai_content_capture="off",
        k_service="kredibel-trace-smoke",
    )  # type: ignore[call-arg]
    setup_tracing(settings)
    tracer = trace.get_tracer("kredibel.smoke")
    run = {
        "langfuse.session.id": "smoke",
        "langfuse.user.id": "org_smoke",
        "langfuse.trace.tags": ("trace_smoke",),
    }
    with (
        tracer.start_as_current_span("workflow:trace_smoke", attributes=run) as root,
        tracer.start_as_current_span(
            "generate_content gemini-smoke",
            attributes={
                "gen_ai.operation.name": "generate_content",
                "gen_ai.request.model": "gemini-smoke",
                "gen_ai.usage.input_tokens": 12,
                "gen_ai.usage.output_tokens": 3,
            },
        ),
    ):
        pass
    trace_id = f"{root.get_span_context().trace_id:032x}"
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    if not provider.force_flush(timeout_millis=10000):
        raise SystemExit("Trace flush timed out. Start Langfuse with make langfuse-up.")
    host = settings.langfuse_host.rstrip("/")
    keys = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key.get_secret_value()}"
    auth = {"Authorization": f"Basic {base64.b64encode(keys.encode()).decode()}"}
    deadline = time.monotonic() + 60  # Langfuse ingests asynchronously through its worker
    while time.monotonic() < deadline:
        try:
            # Langfuse v4 serves observations, not traces, on its public API.
            query = f"traceId={trace_id}&fields=core,basic,usage,model"
            request = Request(f"{host}/api/public/v2/observations?{query}", headers=auth)
            with urlopen(request, timeout=5) as r:
                observations = json.load(r).get("data") or []
            generations = [o for o in observations if o.get("type") == "GENERATION"]
            if generations and generations[0].get("model") == "gemini-smoke":
                total = (generations[0].get("usageDetails") or {}).get("total")
                view = f"{host}/project/kredibel-local/traces/{trace_id}"
                print(f"Verified a generation (model gemini-smoke, {total} tokens): {view}")
                provider.shutdown()
                return
        except HTTPError as error:
            if error.code in (401, 403):
                raise SystemExit("Langfuse refused the keys; run make langfuse-up again.") from None
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    provider.shutdown()
    raise SystemExit(
        "The trace did not reach Langfuse. Check the worker's log: docker compose -f "
        "infra/langfuse/docker-compose.yml logs langfuse-worker"
    )


def main() -> None:
    if "--langfuse" in sys.argv:
        langfuse()
        return
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        trace_export="otlp",
        data_class="synthetic",
        ai_content_capture="off",
        k_service="kredibel-trace-smoke",
    )  # type: ignore[call-arg]
    setup_tracing(settings)
    tracer = trace.get_tracer("kredibel.smoke")
    with (
        tracer.start_as_current_span("workflow:trace_smoke") as root,
        tracer.start_as_current_span("node:synthetic_check") as node,
    ):
        node.set_attribute("kredibel.synthetic", True)
    trace_id = f"{root.get_span_context().trace_id:032x}"
    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    if not provider.force_flush(timeout_millis=10000):
        raise SystemExit("Trace flush timed out. Start the collector with make trace-up.")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:16686/api/traces/{trace_id}", timeout=2) as response:
                data = json.load(response)
            if data.get("data") and len(data["data"][0]["spans"]) == 2:
                print(f"Verified 2 spans: http://localhost:16686/trace/{trace_id}")
                provider.shutdown()
                return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.25)
    provider.shutdown()
    raise SystemExit("Trace was not found in Jaeger. Run make trace-up and check collector logs.")


if __name__ == "__main__":
    main()
