"""No credentials or workspace access: prove local OTLP export and Jaeger ingestion."""

import json
import time
from urllib.error import URLError
from urllib.request import urlopen

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.core.settings import Settings
from app.observability.tracing import setup_tracing


def main() -> None:
    settings = Settings(
        _env_file=None,
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
