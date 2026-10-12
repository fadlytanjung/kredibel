"""Grounding guard for Gemini explanations and assistant answers (spec 008, AC-008-5). Pure."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.findings import Finding

MARKER_REGEX = re.compile(r"\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]")
AMBIGUOUS_SUFFIX_REGEX = re.compile(r"\b\d+(?:\.\d+)?[MKmk]\b")

MONTH_NAMES = (
    "january",
    "jan",
    "february",
    "feb",
    "march",
    "mar",
    "april",
    "apr",
    "may",
    "june",
    "jun",
    "july",
    "jul",
    "august",
    "aug",
    "september",
    "sep",
    "october",
    "oct",
    "november",
    "nov",
    "december",
    "dec",
)


@dataclass(frozen=True)
class Citation:
    kind: str
    id: str
    label: str = ""


@dataclass
class GroundingContext:
    facts: dict[str, Any] = field(default_factory=dict)
    findings: dict[str, Finding] | Sequence[Finding] = field(default_factory=dict)
    documents: set[str] = field(default_factory=set)
    matches: set[str] = field(default_factory=set)
    allowed_fact_prefixes: tuple[str, ...] = ()


@dataclass
class GroundingResult:
    valid: bool
    citations: list[Citation] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    clean_text: str = ""


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences preserving markers."""
    raw = re.split(r"(?<=[.!?\n])\s+", text)
    return [s.strip() for s in raw if s.strip()]


def _parse_decimal(val_str: str) -> Decimal | None:
    try:
        clean = val_str.replace(",", "").strip()
        return Decimal(clean)
    except (InvalidOperation, ValueError):
        return None


def normalize_number_expression(raw_expr: str) -> tuple[Decimal | None, bool]:
    """Normalize a number expression (e.g. '1,250,000', '1.25 million', '64%').

    Returns (value, is_percentage).
    """
    expr = raw_expr.strip()
    is_pct = expr.endswith("%")
    if is_pct:
        expr = expr[:-1].strip()

    is_million = False
    expr_lower = expr.lower()
    if "million" in expr_lower or "juta" in expr_lower:
        is_million = True
        expr = re.sub(r"(?i)\s*(million|juta)", "", expr).strip()

    # Strip currency tokens
    expr = re.sub(r"(?i)^(idr|myr|sgd|usd|eur|jpy|rp\.?|rm)\s*", "", expr).strip()

    # Remove commas
    dec = _parse_decimal(expr)
    if dec is None:
        return None, is_pct

    if is_million:
        dec = dec * Decimal("1000000")

    return dec, is_pct


def check_grounding(text: str, context: GroundingContext) -> GroundingResult:
    """Check that citations resolve and numbers are grounded (AC-008-5)."""
    problems: list[str] = []
    all_citations: list[Citation] = []
    seen_citations: set[tuple[str, str]] = set()

    findings_map: dict[str, Finding] = {}
    if isinstance(context.findings, dict):
        findings_map = context.findings
    else:
        findings_map = {f.finding_id: f for f in context.findings}

    sentences = _split_sentences(text)

    for sentence in sentences:
        # 1. Check for ambiguous formats like 1.25M
        ambiguous_matches = AMBIGUOUS_SUFFIX_REGEX.findall(sentence)
        if ambiguous_matches:
            for amb in ambiguous_matches:
                problems.append(
                    f"Ambiguous number format '{amb}' in sentence '{sentence}': "
                    "use 'million' or explicit number"
                )

        # 2. Extract and resolve markers
        sentence_markers = MARKER_REGEX.findall(sentence)
        sentence_cited_values: set[Decimal] = set()

        for kind, marker_id in sentence_markers:
            key = (kind, marker_id)
            if key not in seen_citations:
                seen_citations.add(key)
                all_citations.append(Citation(kind=kind, id=marker_id, label=f"{kind}:{marker_id}"))

            # Check resolution
            resolved = False
            if kind == "fact":
                # Check turn scoping if restricted
                allowed_pfx = context.allowed_fact_prefixes
                if allowed_pfx and not any(
                    marker_id.startswith(pfx) or f"fact:{marker_id}".startswith(pfx)
                    for pfx in allowed_pfx
                ):
                    problems.append(
                        f"Turn-scoped fact not allowed in context: [[fact:{marker_id}]]"
                    )
                    continue

                fact_val = context.facts.get(marker_id)
                if fact_val is None and not marker_id.startswith("fact:"):
                    fact_val = context.facts.get(f"fact:{marker_id}")

                if fact_val is not None:
                    resolved = True
                    # Record fact value for number checking
                    if isinstance(fact_val, (int, float, Decimal, str)):
                        parsed_val = _parse_decimal(str(fact_val))
                        if parsed_val is not None:
                            sentence_cited_values.add(parsed_val)
                            # Fractional equivalent if applicable (e.g. 64 -> 0.64)
                            if 0 < parsed_val <= 100:
                                sentence_cited_values.add(parsed_val / Decimal("100"))
            elif kind == "finding":
                finding = findings_map.get(marker_id)
                if finding is not None:
                    resolved = True
                    # Extract numbers from finding facts
                    for fact_val in finding.facts.values():
                        parsed_val = _parse_decimal(str(fact_val))
                        if parsed_val is not None:
                            sentence_cited_values.add(parsed_val)
                    if hasattr(finding, "evidence") and isinstance(finding.evidence, dict):
                        for ev_val in finding.evidence.values():
                            parsed_ev = _parse_decimal(str(ev_val))
                            if parsed_ev is not None:
                                sentence_cited_values.add(parsed_ev)
            elif kind == "doc":
                doc_base = marker_id.split("#")[0]
                if doc_base in context.documents:
                    resolved = True
            elif kind == "match":
                if marker_id in context.matches:
                    resolved = True

            if not resolved:
                problems.append(
                    f"Unresolved marker: [[{kind}:{marker_id}]] in sentence '{sentence}'"
                )

        # 3. Check numbers in the sentence
        clean_sentence = MARKER_REGEX.sub("", sentence)

        # Match e.g. IDR 1,250,000, 1.25 million, 64%, 99,000,000
        number_tokens = re.finditer(
            r"(?i)\b(?:idr|myr|sgd|usd|eur|jpy|rp\.?|rm\s*)?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(million|juta)?\s*(%)?",
            clean_sentence,
        )

        for match in number_tokens:
            raw_match = match.group(0).strip()
            num_part = match.group(1)
            million_part = match.group(2)

            start_idx = match.start()
            end_idx = match.end()

            before = clean_sentence[max(0, start_idx - 15) : start_idx].lower()
            after = clean_sentence[end_idx : min(len(clean_sentence), end_idx + 15)].lower()

            is_date_or_year = False
            # Year check: 19xx or 20xx
            if (
                num_part.isdigit()
                and len(num_part) == 4
                and (num_part.startswith("19") or num_part.startswith("20"))
                and not million_part
            ):
                is_date_or_year = True
            # Day + Month check: e.g. "14 March"
            if any(re.search(rf"\b{m}\b", after) for m in MONTH_NAMES) or any(
                re.search(rf"\b{m}\b", before) for m in MONTH_NAMES
            ):
                is_date_or_year = True
            # Page reference check: "page 2", "#p2"
            if re.search(r"\bpages?\b", before) or re.search(r"\bp\d+", before) or "#p" in before:
                is_date_or_year = True
            # Day reference
            if re.search(r"\bdays?\b", before) or re.search(r"\bdays?\b", after):
                is_date_or_year = True

            if is_date_or_year:
                continue

            parsed_dec, is_pct = normalize_number_expression(raw_match)
            if parsed_dec is None:
                continue

            matched = False
            for cited_val in sentence_cited_values:
                if cited_val == parsed_dec:
                    matched = True
                    break
                if is_pct and cited_val == parsed_dec / Decimal("100"):
                    matched = True
                    break

            if not matched:
                problems.append(
                    f"Ungrounded number '{raw_match}' in sentence: '{clean_sentence.strip()}'"
                )

    return GroundingResult(
        valid=len(problems) == 0,
        citations=all_citations,
        problems=problems,
        clean_text=MARKER_REGEX.sub("", text),
    )
