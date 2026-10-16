"""What a run used and cost, from its stages (spec 017, AC-017-5; pricing.v1.yaml). Pure.

Each stage that called a model records the model, its prompt version and the tokens. Code adds them
up and prices them from the policy; a model without a price makes the estimate unavailable, never
zero. Models never compute money.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.domain.models.run import RunStage

MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: Decimal
    output_per_million: Decimal


@dataclass(frozen=True)
class RunUsage:
    models: list[str]
    llm_calls: int
    tokens_in: int
    tokens_out: int
    estimated_usd: Decimal | None
    prompt_versions: dict[str, str] = field(default_factory=dict)


def parse_prices(raw: dict[str, Any]) -> dict[str, ModelPrice]:
    return {
        model: ModelPrice(Decimal(str(p.get("input", "0"))), Decimal(str(p.get("output", "0"))))
        for model, p in (raw.get("perMillionTokens") or {}).items()
    }


def run_usage(stages: list[RunStage], prices: dict[str, ModelPrice]) -> RunUsage:
    calls = [s for s in stages if s.model]
    models = sorted({s.model for s in calls if s.model})
    tokens_in = sum(s.tokens_in or 0 for s in calls)
    tokens_out = sum(s.tokens_out or 0 for s in calls)
    cost: Decimal | None = Decimal(0)
    for s in calls:
        price = prices.get(s.model or "")
        if price is None:
            cost = None
            break
        cost += (
            Decimal(s.tokens_in or 0) * price.input_per_million
            + Decimal(s.tokens_out or 0) * price.output_per_million
        ) / MILLION
    versions: dict[str, str] = {}
    for s in calls:
        if s.prompt_version and "@" in s.prompt_version:
            prompt, version = s.prompt_version.split("@", 1)
            versions[prompt] = version
    return RunUsage(
        models=models,
        llm_calls=len(calls),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_usd=cost.quantize(Decimal("0.001")) if cost is not None else None,
        prompt_versions=dict(sorted(versions.items())),
    )
