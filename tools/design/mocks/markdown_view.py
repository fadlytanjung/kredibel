"""The page Markdown in Preview and Markdown tabs, as the app's MarkdownTabs renders it (spec 023,
AC-023-1): the same small reader (headings, paragraphs, pipe tables, fenced code, lists, rules);
text is escaped, never trusted."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

_COMMON = json.loads((Path(__file__).resolve().parents[3] / "frontend/src/shared/i18n/locales/en/common.json").read_text(encoding="utf-8"))
_TABLE = escape(_COMMON["markdown"]["tableRegion"])
_CODE = escape(_COMMON["markdown"]["codeRegion"])

FENCE = re.compile(r"^```\s*([\w-]*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
ITEM = re.compile(r"^\s*[-*]\s+(.*)$")
DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
INLINE = re.compile(r"\*\*([^*]+)\*\*|`([^`]+)`")


def _cells(line: str) -> list[str]:
    inner = re.sub(r"(?<!\\)\|$", "", line.strip().removeprefix("|"))
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def _row(line: str) -> bool:
    return line.strip().startswith("|")


def _starts(lines: list[str], i: int) -> bool:
    line = lines[i]
    return bool(
        FENCE.match(line) or HEADING.match(line) or RULE.match(line) or ITEM.match(line)
        or (_row(line) and i + 1 < len(lines) and DIVIDER.match(lines[i + 1]))
    )


def inline(text: str) -> str:
    out, last = [], 0
    for m in INLINE.finditer(text):
        if m.start() > last:
            out.append(f"<span>{escape(text[last:m.start()])}</span>")
        out.append(f"<strong>{escape(m.group(1))}</strong>" if m.group(1) is not None else f"<code>{escape(m.group(2))}</code>")
        last = m.end()
    if last < len(text):
        out.append(f"<span>{escape(text[last:])}</span>")
    return "".join(out)


def preview(source: str) -> str:
    lines = source.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if m := FENCE.match(line):
            body = []
            i += 1
            while i < len(lines) and not re.match(r"^```\s*$", lines[i]):
                body.append(lines[i])
                i += 1
            i += 1
            out.append(f'<pre class="md-code" role="region" aria-label="{_CODE}" tabindex="0">{escape(chr(10).join(body))}</pre>')
            continue
        if m := HEADING.match(line):
            level = len(m.group(1))
            tag = ["h3", "h4", "h5", "h6", "h6", "h6"][level - 1]
            out.append(f'<{tag} class="md-h{level}">{inline(m.group(2).strip())}</{tag}>')
            i += 1
            continue
        if RULE.match(line):
            out.append("<hr>")
            i += 1
            continue
        if _row(line) and i + 1 < len(lines) and DIVIDER.match(lines[i + 1]):
            head = "".join(f'<th scope="col">{inline(c)}</th>' for c in _cells(line))
            i += 2
            rows = []
            while i < len(lines) and _row(lines[i]):
                rows.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in _cells(lines[i])) + "</tr>")
                i += 1
            out.append(f'<div class="md-table" role="region" aria-label="{_TABLE}" tabindex="0"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
            continue
        if ITEM.match(line):
            items = []
            while i < len(lines) and (m := ITEM.match(lines[i])):
                items.append(f"<li>{inline(m.group(1))}</li>")
                i += 1
            out.append(f"<ul>{''.join(items)}</ul>")
            continue
        para = []
        while i < len(lines) and lines[i].strip() and (not para or not _starts(lines, i)):
            para.append(f'<span class="md-line">{inline(lines[i])}</span>')
            i += 1
        out.append(f"<p>{''.join(para)}</p>")
    return "".join(out)


def markdown_tabs(source: str, name: str, words) -> str:
    """`words(key, **params)` reads common.json, as the app's t() does."""
    tab = '<button type="button" role="tab" aria-selected="{sel}" class="tab">{label}</button>'
    return (
        '<div class="md-tabs">'
        f'<div class="tabs" role="tablist" aria-label="{escape(words("markdown.tabsAria", name=name))}">'
        + tab.format(sel="true", label=escape(words("markdown.preview")))
        + tab.format(sel="false", label=escape(words("markdown.source")))
        + "</div>"
        f'<div role="tabpanel" class="md-preview" tabindex="0">{preview(source)}</div>'
        "</div>"
    )
