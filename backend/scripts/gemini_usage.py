#!/usr/bin/env python3
"""Gemini usage of the project from Cloud Monitoring (docs/23 §3.4): calls and tokens per model, and
Vertex AI requests by response code, for the last N days.

The application calls Gemini on Vertex AI with Google credentials, never an AI Studio key, so its
usage is here and not on a key. Prints counts only. Uses your application-default credentials
(`gcloud auth application-default login`) and needs roles/monitoring.viewer on the project.

Usage (from backend/): uv run python scripts/gemini_usage.py --days 7
"""

import argparse
import datetime
import sys
from collections import Counter
from typing import Any

import google.auth
import google.auth.transport.requests
import requests

from app.core.settings import Settings

API = "https://monitoring.googleapis.com/v3/projects/{project}/timeSeries"


def series(project: str, token: str, metric: str, resource: str, days: int) -> list[dict[str, Any]]:
    end = datetime.datetime.now(datetime.UTC)
    start = end - datetime.timedelta(days=days)
    params = {
        "filter": f'metric.type="{metric}" AND resource.type="{resource}"',
        "interval.startTime": start.isoformat().replace("+00:00", "Z"),
        "interval.endTime": end.isoformat().replace("+00:00", "Z"),
        "aggregation.alignmentPeriod": f"{days * 86400}s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
    }
    response = requests.get(
        API.format(project=project),
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 403:
        raise SystemExit("Not allowed to read Cloud Monitoring: ask for roles/monitoring.viewer.")
    response.raise_for_status()
    return response.json().get("timeSeries", [])


def total(points: list[dict[str, Any]]) -> int:
    return sum(int(p["value"].get("int64Value", 0)) for p in points)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini usage from Cloud Monitoring")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    project = Settings().google_cloud_project
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(google.auth.transport.requests.Request())  # type: ignore[no-untyped-call]
    token = credentials.token or ""

    model = "aiplatform.googleapis.com/PublisherModel"
    calls: Counter[str] = Counter()
    tokens: Counter[tuple[str, str]] = Counter()
    for ts in series(
        project, token, "aiplatform.googleapis.com/publisher/online_serving/model_invocation_count",
        model, args.days,
    ):  # fmt: skip
        calls[ts["resource"]["labels"].get("model_user_id", "?")] += total(ts.get("points", []))
    for ts in series(
        project, token, "aiplatform.googleapis.com/publisher/online_serving/token_count",
        model, args.days,
    ):  # fmt: skip
        name = ts["resource"]["labels"].get("model_user_id", "?")
        tokens[(name, ts["metric"]["labels"].get("type", "?"))] += total(ts.get("points", []))

    print(f"Gemini on Vertex AI, project {project}, last {args.days} day(s)")
    print(f"{'model':<28}{'calls':>8}{'input tokens':>16}{'output tokens':>16}")
    for name in sorted(calls, key=lambda n: -calls[n]):
        row = f"{name:<28}{calls[name]:>8,}"
        print(f"{row}{tokens[(name, 'input')]:>16,}{tokens[(name, 'output')]:>16,}")
    if not calls:
        print("  no calls recorded")

    codes: Counter[str] = Counter()
    for ts in series(
        project, token, "serviceruntime.googleapis.com/api/request_count", "consumed_api",
        args.days,
    ):  # fmt: skip
        if ts["resource"]["labels"].get("service") != "aiplatform.googleapis.com":
            continue
        method = ts["resource"]["labels"].get("method", "").rsplit(".", 1)[-1]
        if method == "GenerateContent":
            code = ts["metric"]["labels"].get("response_code_class", "?")
            codes[code] += total(ts.get("points", []))
    if codes:
        print(
            "GenerateContent requests by response:",
            ", ".join(f"{c} {n:,}" for c, n in sorted(codes.items())),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
