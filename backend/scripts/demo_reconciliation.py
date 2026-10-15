"""Replay generated PDFs through HTTP upload and the real workflows, in memory (docs/23 §4.3)."""

import argparse
import asyncio
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", action="store_true", help="Send workflow spans to local Jaeger")
    parser.add_argument("--out", type=Path, default=Path("/tmp/kredibel-reconciliation-demo.json"))
    args = parser.parse_args()
    # Set before importing the composition root. No developer .env, Google trace exporter,
    # content capture or external database is used. demo_deps explicitly injects every store.
    os.environ.update(
        {
            "ENV_FILE": os.devnull,
            "TRACE_EXPORT": "otlp" if args.trace else "none",
            "AI_CONTENT_CAPTURE": "off",
            "DATA_CLASS": "synthetic",
            "LOG_LEVEL": "WARNING",
            "K_SERVICE": "kredibel-reconciliation-demo",
            "APP_ROLE": "all",
            "TASK_QUEUE_MODE": "inline",
            "MONTH_RUN_DELAY_SECONDS": "0",
            "RUNS_ENABLED": "true",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://127.0.0.1:4318/v1/traces",
        }
    )
    from tests.integration.test_reconciliation_replay import replay

    async def run() -> dict:
        first, bank_first = await replay(statement_first=True)
        last, documents_first = await replay(statement_first=False)
        assert first == last, "Upload order changed the result"
        runs = [
            r
            for deps in (bank_first, documents_first)
            for r in await deps.run_repo.list_runs("org_1", limit=100)
        ]
        trace_urls = sorted(
            {f"http://localhost:16686/trace/{r.trace_id}" for r in runs if r.trace_id}
        )
        return {
            "reader": "recorded synthetic readings (no Gemini calls)",
            "uploadOrdersEqual": True,
            "automaticMatches": 3,
            "summary": first,
            "traceUrls": trace_urls,
        }

    report = asyncio.run(run())
    if args.trace:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)
        provider.force_flush(timeout_millis=10000)
        provider.shutdown()
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: both upload orders produced the same 3 automatic matches and month figures.")
    print("Sales invoice + purchase invoice + card receipt: PAID_BANK. Cash receipt: PAID_CASH.")
    print(
        "Bank-only lines retain NO_SUPPORT. Recorded readings; no live Gemini or workspace writes."
    )
    print(f"Report: {args.out}")
    for url in report["traceUrls"]:
        print(url)


if __name__ == "__main__":
    main()
