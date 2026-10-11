#!/usr/bin/env python3
"""Build CSS from the design tokens in contracts/design/tokens.json (W3C DTCG format).

Outputs (generated, never edited by hand):
  design/mocks/assets/tokens.css              CSS variables (light + dark) and .type-* classes
  frontend/src/app/styles/tokens.css          same file, when frontend/ exists
  frontend/src/app/styles/tailwind-theme.css  Tailwind v4 `@theme inline` mapping, when frontend/ exists
  frontend/src/app/styles/kit.css             design/mocks/assets/kit.css for the app (ADR-019)
  frontend/src/shared/ui/icons.generated.ts   the mock icon set (tools/design/mocks/icons.py)

Also checks every contrast pair listed in `$extensions["kredibel.contrastPairs"]` (WCAG 2.x ratio).

Usage:
  python3 tools/design/build_tokens.py          write the files, fail on a contrast error
  python3 tools/design/build_tokens.py --check  fail if a generated file is stale (used by `make check`)

Standard library only, so it runs before any project dependency is installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "contracts" / "design" / "tokens.json"
MOCK_CSS = ROOT / "design" / "mocks" / "assets" / "tokens.css"
FE_STYLES = ROOT / "frontend" / "src" / "app" / "styles"

HEADER = (
    "/* GENERATED from contracts/design/tokens.json by tools/design/build_tokens.py.\n"
    "   Do not edit. Change the tokens and run `make tokens`. */\n"
)

ALIAS = re.compile(r"^\{([^}]+)\}$")

KIT_CSS = ROOT / "design" / "mocks" / "assets" / "kit.css"
ICONS_PY = ROOT / "tools" / "design" / "mocks" / "icons.py"
FE_ICONS = ROOT / "frontend" / "src" / "shared" / "ui" / "icons.generated.ts"
FONT_FACE = re.compile(r"@font-face\s*\{[^}]*\}\s*", re.S)
SVG_ELEMENT = re.compile(r"<(\w+)\s+([^>]*?)/>")
SVG_ATTR = re.compile(r'([\w-]+)="([^"]*)"')


# --------------------------------------------------------------------------------------------
# Loading and alias resolution
# --------------------------------------------------------------------------------------------

def load() -> dict:
    return json.loads(TOKENS.read_text(encoding="utf-8"))


def lookup(tree: dict, path: str):
    node = tree
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"unknown token reference {{{path}}}")
        node = node[part]
    return node


def resolve(tree: dict, value, seen: tuple[str, ...] = ()):
    if isinstance(value, str):
        m = ALIAS.match(value)
        if m:
            ref = m.group(1)
            if ref in seen:
                raise ValueError(f"circular token reference: {' -> '.join(seen + (ref,))}")
            target = lookup(tree, ref)
            return resolve(tree, target["$value"], seen + (ref,))
        return value
    if isinstance(value, list):
        return [resolve(tree, v, seen) for v in value]
    if isinstance(value, dict):
        return {k: resolve(tree, v, seen) for k, v in value.items()}
    return value


def leaves(node: dict, prefix: tuple[str, ...] = ()):
    """Yield (path, token) for every token (a dict holding $value) under node."""
    for key, child in node.items():
        if key.startswith("$") or not isinstance(child, dict):
            continue
        if "$value" in child:
            yield prefix + (key,), child
        else:
            yield from leaves(child, prefix + (key,))


# --------------------------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------------------------

def css_value(token_type: str | None, value) -> str:
    if token_type == "fontFamily" or (isinstance(value, list) and value and isinstance(value[0], str)):
        return ", ".join(f'"{v}"' if " " in v else v for v in value)
    if token_type == "cubicBezier":
        return "cubic-bezier({})".format(", ".join(str(v) for v in value))
    if token_type == "shadow":
        layers = value if isinstance(value, list) else [value]
        return ", ".join(
            f"{s['offsetX']} {s['offsetY']} {s['blur']} {s['spread']} {s['color']}" for s in layers
        )
    return str(value)


def var_name(path: tuple[str, ...]) -> str:
    return "--k-" + "-".join(path)


def inherited_type(tree: dict, path: tuple[str, ...]) -> str | None:
    node, found = tree, None
    for part in path:
        node = node[part]
        found = node.get("$type", found)
    return found


# --------------------------------------------------------------------------------------------
# Contrast (WCAG 2.x)
# --------------------------------------------------------------------------------------------

def hex_rgba(h: str) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    if len(h) == 6:
        h += "FF"
    r, g, b, a = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4, 6))
    return r, g, b, a


def over(fg: str, bg: str) -> tuple[float, float, float]:
    r, g, b, a = hex_rgba(fg)
    br, bgc, bb, _ = hex_rgba(bg)
    return r * a + br * (1 - a), g * a + bgc * (1 - a), b * a + bb * (1 - a)


def luminance(rgb: tuple[float, float, float]) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str, base: str) -> float:
    bg_rgb = over(bg, base)
    bg_hex = "#" + "".join(f"{round(c * 255):02X}" for c in bg_rgb)
    l1, l2 = luminance(over(fg, bg_hex)), luminance(bg_rgb)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast(tree: dict) -> list[str]:
    errors = []
    for fg_path, bg_path, minimum in tree["$extensions"]["kredibel.contrastPairs"]:
        theme = fg_path.split(".")[0]
        base = resolve(tree, lookup(tree, f"{theme}.color.bg.surface")["$value"])
        fg = resolve(tree, lookup(tree, fg_path)["$value"])
        bg = resolve(tree, lookup(tree, bg_path)["$value"])
        r = ratio(fg, bg, base)
        status = "ok " if r >= minimum else "LOW"
        print(f"  {status} {r:5.2f} (min {minimum}) {fg_path} on {bg_path}")
        if r < minimum:
            errors.append(f"{fg_path} on {bg_path}: {r:.2f} < {minimum}")
    return errors


# --------------------------------------------------------------------------------------------
# tokens.css
# --------------------------------------------------------------------------------------------

def theme_block(tree: dict, theme: str) -> list[str]:
    lines = []
    for path, tok in leaves(tree[theme]):
        value = resolve(tree, tok["$value"])
        lines.append(f"  {var_name(path)}: {css_value('color', value)};")
    return lines


def scale_block(tree: dict) -> list[str]:
    lines = []
    for group in ("font", "space", "radius", "shadow", "border-width", "motion", "layout", "z"):
        for path, tok in leaves(tree[group], (group,)):
            value = resolve(tree, tok["$value"])
            lines.append(f"  {var_name(path)}: {css_value(inherited_type(tree, path), value)};")
    return lines


def typography_classes(tree: dict) -> list[str]:
    out = []
    compact = []
    for name, tok in leaves(tree["typography"]):
        name = name[0]
        v = resolve(tree, tok["$value"])
        ext = tok.get("$extensions", {})
        decl = [
            "font-family: var(--k-font-family-sans);",
            f"font-size: {v['fontSize']};",
            f"line-height: {v['lineHeight']};",
            f"font-weight: {v['fontWeight']};",
            f"letter-spacing: {v['letterSpacing']};",
        ]
        if "kredibel.stretch" in ext:
            decl.append(f"font-stretch: {ext['kredibel.stretch']}%;")
        if "kredibel.numeric" in ext:
            decl.append(f"font-variant-numeric: {ext['kredibel.numeric']};")
        out.append(f".type-{name} {{ " + " ".join(decl) + " }")
        if "kredibel.compact" in ext:
            c = ext["kredibel.compact"]
            compact.append(
                f"  .type-{name} {{ font-size: {c['fontSize']}; line-height: {c['lineHeight']}; }}"
            )
    if compact:
        bp = resolve(tree, tree["layout"]["breakpoint"]["medium"]["$value"])
        out.append(f"@media (width < {bp}) {{")
        out.extend(compact)
        out.append("}")
    return out


def build_tokens_css(tree: dict) -> str:
    parts = [HEADER, ":root {", *scale_block(tree), *theme_block(tree, "light"), "}", ""]
    parts += ["/* Dark theme (P2): opt-in with <html data-theme=\"dark\"> until it is reviewed. */",
              ':root[data-theme="dark"] {', *theme_block(tree, "dark"), "}", ""]
    parts += ["/* Typography styles */", *typography_classes(tree), ""]
    return "\n".join(parts)


# --------------------------------------------------------------------------------------------
# tailwind-theme.css
# --------------------------------------------------------------------------------------------

def tw_color_name(path: tuple[str, ...]) -> str:
    """light.color.<path> -> Tailwind colour name (bg-<name>, text-<name>, border-<name>)."""
    head, rest = path[0], path[1:]
    if head == "bg":
        return rest[0]                                       # canvas, surface, sunken, raised, inverse
    if head == "text":
        return {"default": "ink", "muted": "ink-muted", "subtle": "ink-subtle"}.get(rest[0], rest[0])
    if head == "border":
        return "line" if rest[0] == "default" else f"line-{rest[0]}"
    if head in ("brand", "evidence"):
        return head if rest[0] == "default" else f"{head}-{rest[0]}"
    if head in ("severity", "verdict"):
        return rest[0] + {"fg": "", "bg": "-soft", "line": "-line"}[rest[1]]
    if head == "reading":
        return rest[0]                                        # agreed, single-source, conflict
    if head == "focus":
        return "focus"
    return "-".join(path)                                     # grade-a, chart-inflow, scrim


def build_tailwind_theme(tree: dict) -> str:
    lines = [HEADER, '@import "./tokens.css";', "", "@theme inline {",
             "  --color-*: initial;", "  --breakpoint-*: initial;",
             "  --color-transparent: transparent;", "  --color-current: currentColor;"]
    for path, _ in leaves(tree["light"]["color"]):
        lines.append(f"  --color-{tw_color_name(path)}: var({var_name(('color',) + path)});")
    lines.append("  --font-sans: var(--k-font-family-sans);")
    lines.append("  --spacing: 4px;")
    for path, _ in leaves(tree["radius"], ("radius",)):
        lines.append(f"  --radius-{path[-1]}: var({var_name(path)});")
    for path, _ in leaves(tree["shadow"], ("shadow",)):
        lines.append(f"  --shadow-{path[-1]}: var({var_name(path)});")
    for path, _ in leaves(tree["motion"]["easing"], ("motion", "easing")):
        lines.append(f"  --ease-{path[-1]}: var({var_name(path)});")
    for path, tok in leaves(tree["layout"]["breakpoint"], ("layout", "breakpoint")):
        lines.append(f"  --breakpoint-{path[-1]}: {resolve(tree, tok['$value'])};")
        lines.append(f"  --container-{path[-1]}: {resolve(tree, tok['$value'])};")
    lines.append("}")
    lines.append("")
    lines.append("@utility num { font-variant-numeric: tabular-nums lining-nums; }")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------
# One component stylesheet and one icon set for the mocks and the app (ADR-019)
# --------------------------------------------------------------------------------------------

def build_app_kit_css() -> str:
    """kit.css as the app's component layer. The @font-face is dropped: the app loads the same
    Archivo variable font (weight and width axes) from @fontsource-variable/archivo/wdth.css."""
    header = (
        "/* GENERATED from design/mocks/assets/kit.css by tools/design/build_tokens.py (ADR-019).\n"
        "   Do not edit. Change design/mocks/assets/kit.css and run `make tokens`. */\n"
    )
    return header + FONT_FACE.sub("", KIT_CSS.read_text(encoding="utf-8"), count=1)


def build_icons_ts() -> str:
    """The mock icons as element data, so React draws them without raw HTML."""
    namespace: dict = {}
    exec(compile(ICONS_PY.read_text(encoding="utf-8"), str(ICONS_PY), "exec"), namespace)
    lines = [
        "/* GENERATED from tools/design/mocks/icons.py by tools/design/build_tokens.py (ADR-019).",
        "   Do not edit. Change the icon in icons.py and run `make tokens`. */",
        "",
        "export type IconElement = { tag: 'path' | 'circle' | 'rect'; attrs: Record<string, string> }",
        "",
        "export const ICONS = {",
    ]
    for name in sorted(namespace["ICONS"]):
        elements = []
        for tag, attrs in SVG_ELEMENT.findall(namespace["ICONS"][name]):
            pairs = ", ".join(f"{key}: {json.dumps(value)}" for key, value in SVG_ATTR.findall(attrs))
            elements.append(f"{{ tag: '{tag}', attrs: {{ {pairs} }} }}")
        lines.append(f"  {json.dumps(name)}: [{', '.join(elements)}],")
    lines += ["} satisfies Record<string, IconElement[]>", "", "export type IconName = keyof typeof ICONS", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = ap.parse_args()

    tree = load()
    print("Contrast:")
    errors = check_contrast(tree)

    outputs = {MOCK_CSS: build_tokens_css(tree)}
    if (ROOT / "frontend").is_dir():
        outputs[FE_STYLES / "tokens.css"] = outputs[MOCK_CSS]
        outputs[FE_STYLES / "tailwind-theme.css"] = build_tailwind_theme(tree)
        outputs[FE_STYLES / "kit.css"] = build_app_kit_css()
        outputs[FE_ICONS] = build_icons_ts()

    for path, text in outputs.items():
        rel = path.relative_to(ROOT)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                errors.append(f"{rel} is stale: run `make tokens`")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {rel}")

    if errors:
        print("\n".join(["", "Design token errors:", *("  - " + e for e in errors)]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
