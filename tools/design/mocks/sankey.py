"""A small, dependency-free Sankey layout for the mocks (the app uses d3-sankey with the same look).
Three columns: sources -> one bank account -> uses. Values in IDR millions (synthetic S1, Jan–Jun 2026)."""

import json
from pathlib import Path

# The app's own chart words (dashboard.json), so the compact lists read the same in both (AC-019-2).
DASH_WORDS = json.loads((Path(__file__).resolve().parents[3] / "frontend/src/shared/i18n/locales/en/dashboard.json").read_text(encoding="utf-8"))

SOURCES = [
    ("Harborview Hotel Group", 412.5),
    ("Highland Resort & Spa", 318.0),
    ("Daybreak Café", 196.4),
    ("Spice Route Restaurant", 154.8),
    ("Hillside Coffee Bar", 121.6),
    ("Other clients", 88.2),
    ("Cash deposits", 64.3),
]
USES = [
    ("Suppliers", 612.4, "out"),
    ("Payroll", 270.0, "out"),
    ("Rent and utilities", 118.6, "out"),
    ("Tax", 96.2, "out"),
    ("Owner drawings", 72.0, "out"),
    ("Loan payments", 60.0, "out"),
    ("Other spending", 57.6, "out"),
    ("Kept in the account", 69.0, "kept"),
]
TOTAL = round(sum(v for _, v in SOURCES), 1)
assert abs(TOTAL - sum(v for _, v, _ in USES)) < 0.05


def fmt(v: float) -> str:
    return f"{v:,.1f}"


def band(x0, y0a, y0b, x1, y1a, y1b, cls, label):
    xm = (x0 + x1) / 2
    d = (f"M{x0:.1f},{y0a:.1f} C{xm:.1f},{y0a:.1f} {xm:.1f},{y1a:.1f} {x1:.1f},{y1a:.1f} "
         f"L{x1:.1f},{y1b:.1f} C{xm:.1f},{y1b:.1f} {xm:.1f},{y0b:.1f} {x0:.1f},{y0b:.1f} Z")
    return f'<path class="band {cls}" d="{d}"><title>{label}</title></path>'


def sankey_svg(hot: str | None = "Suppliers") -> str:
    W = 900
    top = 62
    k = 0.255           # px per million
    gap = 10
    xs0, xs1 = 232, 242          # source nodes
    xa0, xa1 = 452, 470          # account node
    xu0, xu1 = 680, 690          # use nodes
    acc_h = TOTAL * k
    src_h = acc_h + gap * (len(SOURCES) - 1)
    use_h = acc_h + gap * (len(USES) - 1)
    span = max(src_h, use_h)
    H = round(top + span + 14)
    acc_y = top + (span - acc_h) / 2
    acc_x = (xa0 + xa1) / 2
    parts = [f'<svg class="sankey" viewBox="0 0 {W} {H}" role="group" aria-labelledby="flow-title flow-desc">',
             '<title id="flow-title">Money flow, January to June 2026</title>',
             f'<desc id="flow-desc">IDR {fmt(TOTAL)} million came into ACB account ending 4821 from seven sources and went to eight uses, including {fmt(69.0)} million kept in the account. A table version follows the chart.</desc>',
             f'<text class="col" x="{xs1}" y="18" text-anchor="end">Money in</text>',
             f'<text class="col" x="{acc_x}" y="18" text-anchor="middle">Account</text>',
             f'<text class="col" x="{xu0}" y="18">Money out</text>']
    y = top + (span - src_h) / 2
    ay = acc_y
    bands, nodes, labels = [], [], []
    for name, v in SOURCES:
        h = v * k
        bands.append(band(xs1, y, y + h, xa0, ay, ay + h, "", f"{name} to ACB ••4821: IDR {fmt(v)} M"))
        nodes.append(f'<rect class="node src" x="{xs0}" y="{y:.1f}" width="{xs1 - xs0}" height="{h:.1f}"/>')
        ty = y + h / 2 + 5
        labels.append(f'<text x="{xs0 - 8}" y="{ty:.1f}" text-anchor="end">{name.replace("&", "&amp;")} <tspan class="amt">{fmt(v)}</tspan></text>')
        y += h + gap
        ay += h
    y = top + (span - use_h) / 2
    ay = acc_y
    for name, v, kind in USES:
        h = v * k
        cls = "kept" if kind == "kept" else "out"
        if hot and name == hot:
            cls += " is-hot"
        bands.append(band(xa1, ay, ay + h, xu0, y, y + h, cls, f"ACB ••4821 to {name}: IDR {fmt(v)} M"))
        ncls = "kept" if kind == "kept" else "use"
        nodes.append(f'<rect class="node {ncls}" x="{xu0}" y="{y:.1f}" width="{xu1 - xu0}" height="{h:.1f}"/>')
        ty = y + h / 2 + 5
        weight = ' font-weight="640"' if kind == "kept" else ""
        labels.append(f'<text x="{xu1 + 8}" y="{ty:.1f}"{weight}>{name} <tspan class="amt">{fmt(v)}</tspan></text>')
        y += h + gap
        ay += h
    nodes.append(f'<rect class="node acc" x="{xa0}" y="{acc_y:.1f}" width="{xa1 - xa0}" height="{acc_h:.1f}"/>')
    labels.append(f'<text class="acc-label" x="{acc_x}" y="{acc_y - 26:.1f}" text-anchor="middle">ACB ••4821</text>')
    labels.append(f'<text class="amt" x="{acc_x}" y="{acc_y - 9:.1f}" text-anchor="middle">{fmt(TOTAL)} through it</text>')
    parts += bands + nodes + labels
    if hot:
        tx, ty = 478, top + 56
        parts.append(f'<g class="tip" transform="translate({tx} {ty})">'
                     f'<rect x="0" y="0" width="196" height="60" rx="10" fill="var(--k-color-bg-inverse)"/>'
                     f'<text x="14" y="25" style="fill:var(--k-color-text-on-inverse);font-weight:640">Suppliers: 612.4</text>'
                     f'<text x="14" y="46" style="fill:var(--k-color-text-on-inverse);font-size:13px;opacity:.82">38 bank lines. Click to list</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def flow_list() -> str:
    top_in = SOURCES[:3]
    top_out = [u for u in USES if u[2] == "out"][:3]
    mx = max(v for _, v in SOURCES + [(u[0], u[1]) for u in USES])
    def row(name, v, cls=""):
        return (f'<div class="flow-row {cls}"><span>{name.replace("&", "&amp;")}</span><span class="amt">{fmt(v)}</span>'
                f'<span class="bar"><i style="width:{v / mx * 100:.0f}%"></i></span></div>')
    ins = "".join(row(n, v) for n, v in top_in)
    outs = "".join(row(n, v, "out") for n, v, _ in top_out)
    kept = row("Kept in the account", 69.0, "kept")
    came, went = DASH_WORDS["charts"]["cameFrom"], DASH_WORDS["charts"]["wentTo"]
    return (f'<div class="flow-list"><section aria-label="{came}"><h3>{came}</h3>{ins}</section>'
            f'<section aria-label="{went}"><h3>{went}</h3>{outs}{kept}</section></div>')


def flow_table() -> str:
    rows = "".join(f"<tr><td>{n.replace('&', '&amp;')}</td><td>ACB ••4821</td><td class=\"r\">{fmt(v)}</td></tr>" for n, v in SOURCES)
    rows += "".join(f"<tr><td>ACB ••4821</td><td>{n}</td><td class=\"r\">{fmt(v)}</td></tr>" for n, v, _ in USES)
    return f'<table class="sr-only"><caption>Money flow as a table, IDR millions</caption><thead><tr><th>From</th><th>To</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>'
