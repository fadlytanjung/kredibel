"""Prompt files (docs/06 §6): one Markdown file per LLM call, with front matter; `id@version` is
recorded on every run and is part of the extraction cache key."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "agents" / "prompts"


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    model_env: str
    output_schema: str
    text: str

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


@cache
def load_prompt(name: str) -> Prompt:
    raw = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front)
    return Prompt(
        id=meta["id"],
        version=int(meta["version"]),
        model_env=meta["model_env"],
        output_schema=meta["output_schema"],
        text=body.strip(),
    )
