"""Dashboard charts for the mocks: the money flow by statement line (IFRS or US GAAP), spending bars,
money in and out by month, net by month, and the cash-flow statement as a waterfall.

All values are IDR millions for the demo workspace (docs/18), January to June 2026. Totals agree with
the dashboard figures: in 1,355.8, out 1,286.8, kept 69.0. The app draws the same charts from
GET /api/money-flow and GET /api/cash-flow; categories, statement lines and cash-flow classes come from
contracts/policy/categories.v1.yaml."""

from __future__ import annotations

# ----------------------------------------------------------------------------------------------- data

ACCOUNT = "ACB ••4821"
REVENUE = [  # sources: all revenue, by client
    ("Harborview Hotel Group", 412.5),
    ("Highland Resort & Spa", 318.0),
    ("Daybreak Café", 196.4),
    ("Spice Route Restaurant", 154.8),
    ("Hillside Coffee Bar", 121.6),
    ("Other clients", 88.2),
    ("Cash sales deposited", 64.3),
]
# (line key, label by framework, value, IFRS activity, US GAAP activity)
LINES = [
    ("cos", {"IFRS": "Cost of sales", "US_GAAP": "Cost of goods sold"}, 563.9, "OPERATING", "OPERATING"),
    ("payroll", {"IFRS": "Payroll", "US_GAAP": "Payroll"}, 270.0, "OPERATING", "OPERATING"),
    ("rent", {"IFRS": "Rent and utilities", "US_GAAP": "Rent and utilities"}, 118.6, "OPERATING", "OPERATING"),
    ("repairs", {"IFRS": "Repairs and services", "US_GAAP": "Repairs and services"}, 48.5, "OPERATING", "OPERATING"),
    ("other", {"IFRS": "Other operating expenses", "US_GAAP": "Other SG&A"}, 57.6, "OPERATING", "OPERATING"),
    ("tax", {"IFRS": "Taxes paid", "US_GAAP": "Taxes paid"}, 96.2, "OPERATING", "OPERATING"),
    ("interest", {"IFRS": "Finance costs (interest)", "US_GAAP": "Interest expense"}, 12.0, "FINANCING", "OPERATING"),
    ("loan", {"IFRS": "Loan principal repaid", "US_GAAP": "Loan principal repaid"}, 48.0, "FINANCING", "FINANCING"),
    ("owner", {"IFRS": "Owner drawings", "US_GAAP": "Owner drawings"}, 72.0, "FINANCING", "FINANCING"),
]
KEPT = 69.0
OPENING, CLOSING = 29.3, 98.3
MONTHS = [("Jan", 221.6, 209.8), ("Feb", 214.9, 208.1), ("Mar", 231.4, 218.9),
          ("Apr", 226.3, 212.0), ("May", 229.8, 224.6), ("Jun", 231.8, 213.4)]
ACTIVITY_LABEL = {"OPERATING": "Operating", "INVESTING": "Investing", "FINANCING": "Financing"}

TOTAL_IN = round(sum(v for _, v in REVENUE), 1)
TOTAL_OUT = round(sum(l[2] for l in LINES), 1)
assert abs(TOTAL_IN - 1355.8) < 0.05 and abs(TOTAL_OUT - 1286.8) < 0.05
assert abs(sum(m[1] for m in MONTHS) - TOTAL_IN) < 0.05 and abs(sum(m[2] for m in MONTHS) - TOTAL_OUT) < 0.05
assert abs(OPENING + TOTAL_IN - TOTAL_OUT - CLOSING) < 0.05


def fmt(v: float, sign: bool = False) -> str:
    s = f"{abs(v):,.1f}"
    if sign:
        return ("+" if v >= 0 else "−") + s
    return s


def esc(s: str) -> str:
    return s.replace("&", "&amp;")


def activity_totals(fw: str) -> dict[str, float]:
    key = 3 if fw == "IFRS" else 4
    out = {"OPERATING": 0.0, "INVESTING": 0.0, "FINANCING": 0.0}
    for line in LINES:
        out[line[key]] += line[2]
    return {k: round(v, 1) for k, v in out.items()}


# ------------------------------------------------------------------------------------ sankey engine

def _band(x0, y0a, y0b, x1, y1a, y1b, cls, title):
    xm = (x0 + x1) / 2
    d = (f"M{x0:.1f},{y0a:.1f} C{xm:.1f},{y0a:.1f} {xm:.1f},{y1a:.1f} {x1:.1f},{y1a:.1f} "
         f"L{x1:.1f},{y1b:.1f} C{xm:.1f},{y1b:.1f} {xm:.1f},{y0b:.1f} {x0:.1f},{y0b:.1f} Z")
    return f'<path class="band {cls}" d="{d}" tabindex="0"><title>{esc(title)}</title></path>'


def sankey(columns: list[dict], links: list[tuple], width: int, height: int, k: float, top: int,
           title: str, desc: str, headers: list[tuple[str, float, str]]) -> str:
    """columns: [{x, w, gap, nodes: [(id, label, value, cls, labelPos)]}]; links: (src, tgt, value, cls, title).
    labelPos: 'left', 'right' or 'above'."""
    pos = {}
    for col in columns:
        h = sum(n[2] for n in col["nodes"]) * k + col["gap"] * (len(col["nodes"]) - 1)
        y = top + col.get("offset", 0)
        for nid, label, value, cls, lp in col["nodes"]:
            nh = value * k
            pos[nid] = {"x": col["x"], "w": col["w"], "y": y, "h": nh, "label": label, "value": value,
                        "cls": cls, "lp": lp, "out": 0.0, "in": 0.0}
            y += nh + col["gap"]
        col["h"] = h
    parts = [f'<svg class="chart sankey" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{title[0]} {desc[0]}">',
             f'<title id="{title[0]}">{esc(title[1])}</title><desc id="{desc[0]}">{esc(desc[1])}</desc>']
    for text, x, anchor in headers:
        parts.append(f'<text class="col" x="{x}" y="18" text-anchor="{anchor}">{text}</text>')
    # order links: by source y then target y
    links = sorted(links, key=lambda l: (pos[l[0]]["y"], pos[l[1]]["y"]))
    bands = []
    for src, tgt, value, cls, ttl in links:
        s, t = pos[src], pos[tgt]
        h = value * k
        y0 = s["y"] + s["out"]
        s["out"] += h
        bands.append((src, tgt, s["x"] + s["w"], y0, y0 + h, t, h, cls, ttl))
    # target offsets in order of source position
    for src, tgt, x0, y0a, y0b, t, h, cls, ttl in sorted(bands, key=lambda b: (pos[b[1]]["y"], pos[b[0]]["y"])):
        y1 = t["y"] + t["in"]
        t["in"] += h
        parts.append(_band(x0, y0a, y0b, t["x"], y1, y1 + h, cls, ttl))
    for nid, n in pos.items():
        parts.append(f'<rect class="node {n["cls"]}" x="{n["x"]}" y="{n["y"]:.1f}" width="{n["w"]}" height="{n["h"]:.1f}"/>')
    for nid, n in pos.items():
        cy = n["y"] + n["h"] / 2 + 5
        lab = f'{esc(n["label"])} <tspan class="amt">{fmt(n["value"])}</tspan>'
        if n["lp"] == "left":
            parts.append(f'<text x="{n["x"] - 8}" y="{cy:.1f}" text-anchor="end">{lab}</text>')
        elif n["lp"] == "right":
            parts.append(f'<text x="{n["x"] + n["w"] + 8}" y="{cy:.1f}">{lab}</text>')
        else:  # above, centred on the node
            cx = n["x"] + n["w"] / 2
            parts.append(f'<text class="node-label" x="{cx}" y="{n["y"] - 8:.1f}" text-anchor="middle">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------------------------------------- charts

def statement_sankey(fw: str = "IFRS", width: int = 1200) -> str:
    """Revenue by client → account → cash-flow activity (by framework) → statement line.
    width 1200 for wide panels, 860 for medium ones (tablets), so the labels stay readable."""
    xs, hx = ((240, 472, 712, 950), (250, 480, 718, 950)) if width >= 1200 else ((228, 368, 506, 628), (238, 376, 512, 628))
    acts = activity_totals(fw)
    key = 3 if fw == "IFRS" else 4
    act_nodes = [("act_OPERATING", "Operating", acts["OPERATING"], "operating", "above")]
    if acts["INVESTING"] > 0:
        act_nodes.append(("act_INVESTING", "Investing", acts["INVESTING"], "investing", "above"))
    act_nodes.append(("act_FINANCING", "Financing", acts["FINANCING"], "financing", "above"))
    act_nodes.append(("kept", "Kept", KEPT, "kept", "above"))
    order = sorted(LINES, key=lambda l: (["OPERATING", "INVESTING", "FINANCING"].index(l[key]), LINES.index(l)))
    line_nodes = [(f"line_{l[0]}", l[1][fw], l[2], l[key].lower(), "right") for l in order]
    columns = [
        {"x": xs[0], "w": 10, "gap": 10, "nodes": [(f"src{i}", n, v, "src", "left") for i, (n, v) in enumerate(REVENUE)]},
        {"x": xs[1], "w": 16, "gap": 0, "offset": 30, "nodes": [("acc", ACCOUNT, TOTAL_IN, "acc", "above")]},
        {"x": xs[2], "w": 12, "gap": 28, "offset": 18, "nodes": act_nodes},
        {"x": xs[3], "w": 10, "gap": 10, "nodes": line_nodes},
    ]
    links = [(f"src{i}", "acc", v, "", f"{n} to {ACCOUNT}: IDR {fmt(v)} M") for i, (n, v) in enumerate(REVENUE)]
    for nid, label, value, cls, _ in act_nodes:
        links.append(("acc", nid, value, cls, f"{ACCOUNT} to {label}: IDR {fmt(value)} M"))
    for l in order:
        links.append((f"act_{l[key]}", f"line_{l[0]}", l[2], l[key].lower(), f"{ACCOUNT}, {ACTIVITY_LABEL[l[key]]}: {l[1][fw]}, IDR {fmt(l[2])} M"))
    fwname = "IFRS" if fw == "IFRS" else "US GAAP"
    return sankey(
        columns, links, width, 530, 0.29, 44,
        (f"flow-t-{fw}-{width}", f"Where the money went, January to June 2026, {fwname}"),
        (f"flow-d-{fw}-{width}", f"IDR {fmt(TOTAL_IN)} million of revenue came into {ACCOUNT}. Operating activities used {fmt(acts['OPERATING'])} million, financing activities {fmt(acts['FINANCING'])} million, and {fmt(KEPT)} million was kept. A table version follows."),
        [("Revenue, by client", hx[0], "end"), ("Account", hx[1], "middle"), (f"Activity ({fwname})", hx[2], "middle"), ("Statement line", hx[3], "start")],
    )


def spend_bars(fw: str = "IFRS") -> str:
    """Horizontal bars by statement line, grouped by activity (HTML, so it reflows on any width)."""
    key = 3 if fw == "IFRS" else 4
    mx = max(l[2] for l in LINES)
    groups = []
    for act in ("OPERATING", "FINANCING"):
        rows = [l for l in LINES if l[key] == act]
        total = sum(l[2] for l in rows)
        items = "".join(
            f'<li class="hbar {act.lower()}"><span class="name">{esc(l[1][fw])}</span><span class="track"><i style="width:{l[2] / mx * 100:.1f}%"></i></span><span class="val">{fmt(l[2])}</span></li>'
            for l in rows)
        groups.append(f'<div class="hbar-group"><h3>{ACTIVITY_LABEL[act]} <span class="amt">{fmt(total)}</span></h3><ul>{items}</ul></div>')
    kept = f'<div class="hbar-group"><h3>Kept in the account <span class="amt">{fmt(KEPT)}</span></h3><ul><li class="hbar kept"><span class="name">Closing minus opening balance</span><span class="track"><i style="width:{KEPT / mx * 100:.1f}%"></i></span><span class="val">{fmt(KEPT)}</span></li></ul></div>'
    return f'<div class="hbars">{"".join(groups)}{kept}</div>'


def flow_table(fw: str = "IFRS") -> str:
    key = 3 if fw == "IFRS" else 4
    rows = "".join(f"<tr><td>{esc(n)}</td><td>Revenue</td><td class=\"r\">{fmt(v)}</td></tr>" for n, v in REVENUE)
    rows += "".join(f"<tr><td>{esc(l[1][fw])}</td><td>{ACTIVITY_LABEL[l[key]]}</td><td class=\"r\">−{fmt(l[2])}</td></tr>" for l in LINES)
    rows += f'<tr class="total"><td>Kept in the account</td><td></td><td class="r">{fmt(KEPT)}</td></tr>'
    return (f'<div class="chart-table-wrap"><table class="data-table chart-table"><caption class="sr-only">Money flow by statement line, IDR millions</caption>'
            f'<thead><tr><th>Line</th><th>Activity</th><th class="r">IDR M</th></tr></thead><tbody>{rows}</tbody></table></div>')


def _axis(x0, x1, y_of, ticks, width_labels=46):
    out = []
    for v in ticks:
        y = y_of(v)
        out.append(f'<line class="grid" x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="tick" x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end">{v:,.0f}</text>')
    return "".join(out)


def monthly_bars(compact: bool = False, medium: bool = False) -> str:
    """Money in and out by month (grouped bars) with the net above each pair."""
    W, H = (380, 260) if compact else ((800, 300) if medium else (1200, 320))
    left, right, top, bottom = (40, 10, 30, 36) if compact else (64, 24, 36, 40)
    vmax = 250.0
    plot_h = H - top - bottom
    y_of = lambda v: top + plot_h - v / vmax * plot_h
    n = len(MONTHS)
    slot = (W - left - right) / n
    bw = slot * (0.26 if compact else 0.22)
    parts = [f'<svg class="chart bars" viewBox="0 0 {W} {H}" role="img" aria-label="Money in and out by month, January to June 2026, IDR millions">',
             _axis(left, W - right, y_of, [0, 100, 200] if compact else [0, 50, 100, 150, 200, 250])]
    for i, (m, vin, vout) in enumerate(MONTHS):
        cx = left + slot * i + slot / 2
        hot = " is-hot" if m == "Mar" else ""
        parts.append(f'<rect class="bar in{hot}" x="{cx - bw - 2:.1f}" y="{y_of(vin):.1f}" width="{bw:.1f}" height="{y_of(0) - y_of(vin):.1f}" rx="3"><title>{m} money in: {fmt(vin)}</title></rect>')
        parts.append(f'<rect class="bar out{hot}" x="{cx + 2:.1f}" y="{y_of(vout):.1f}" width="{bw:.1f}" height="{y_of(0) - y_of(vout):.1f}" rx="3"><title>{m} money out: {fmt(vout)}</title></rect>')
        parts.append(f'<text class="net" x="{cx:.1f}" y="{y_of(max(vin, vout)) - 8:.1f}" text-anchor="middle">{fmt(vin - vout, True)}</text>')
        parts.append(f'<text class="tick" x="{cx:.1f}" y="{H - bottom + 22:.1f}" text-anchor="middle">{m}</text>')
        if not compact:
            parts.append(f'<text class="bar-val" x="{cx - bw / 2 - 2:.1f}" y="{y_of(vin) + 16:.1f}" text-anchor="middle">{vin:.0f}</text>'
                         f'<text class="bar-val dark" x="{cx + bw / 2 + 2:.1f}" y="{y_of(vout) + 16:.1f}" text-anchor="middle">{vout:.0f}</text>')
    parts.append("</svg>")
    return "".join(parts)


def net_bars(compact: bool = False, medium: bool = False) -> str:
    """Net cash flow per month, with the balance at month end as a dashed line."""
    W, H = (380, 240) if compact else ((800, 280) if medium else (1200, 300))
    left, right, top, bottom = (40, 10, 30, 36) if compact else (64, 24, 36, 40)
    plot_h = H - top - bottom
    vmax = 100.0
    y_of = lambda v: top + plot_h - v / vmax * plot_h
    n = len(MONTHS)
    slot = (W - left - right) / n
    bw = slot * (0.36 if compact else 0.3)
    parts = [f'<svg class="chart bars" viewBox="0 0 {W} {H}" role="img" aria-label="Net cash flow and month-end balance, IDR millions">',
             _axis(left, W - right, y_of, [0, 50, 100] if compact else [0, 25, 50, 75, 100])]
    bal = OPENING
    pts = []
    for i, (m, vin, vout) in enumerate(MONTHS):
        cx = left + slot * i + slot / 2
        net = vin - vout
        bal += net
        parts.append(f'<rect class="bar net-bar" x="{cx - bw / 2:.1f}" y="{y_of(net):.1f}" width="{bw:.1f}" height="{y_of(0) - y_of(net):.1f}" rx="3"><title>{m} net: {fmt(net, True)}</title></rect>')
        parts.append(f'<text class="net" x="{cx:.1f}" y="{y_of(net) - 8:.1f}" text-anchor="middle">{fmt(net, True)}</text>')
        parts.append(f'<text class="tick" x="{cx:.1f}" y="{H - bottom + 22:.1f}" text-anchor="middle">{m}</text>')
        pts.append((cx, y_of(bal), bal))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y, _) in enumerate(pts))
    parts.append(f'<path class="balance-line" d="{path}"/>')
    for x, y, b in pts:
        parts.append(f'<circle class="balance-dot" cx="{x:.1f}" cy="{y:.1f}" r="4"><title>Balance {fmt(b)}</title></circle>')
    lx, ly, lb = pts[-1]
    parts.append(f'<text class="bar-val dark" x="{lx - 10:.1f}" y="{ly - 10:.1f}" text-anchor="end">Balance {fmt(lb)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def waterfall(fw: str = "IFRS", compact: bool = False, medium: bool = False) -> str:
    """Cash-flow statement: opening → operating → investing → financing → closing."""
    acts = activity_totals(fw)
    op = round(TOTAL_IN - acts["OPERATING"], 1)
    inv = -acts["INVESTING"]
    fin = -acts["FINANCING"]
    steps = [("Opening balance", OPENING, "total"), ("Operating activities", op, "operating"),
             ("Investing activities", inv, "investing"), ("Financing activities", fin, "financing"),
             ("Closing balance", CLOSING, "total")]
    W = 380 if compact else (800 if medium else 1200)
    label_w = 150 if compact else (200 if medium else 250)
    right = 64 if compact else (90 if medium else 120)
    row_h, top = (40, 12) if compact else (46, 16)
    H = top + row_h * len(steps) + 10
    vmax = OPENING + max(op, 0) + 10
    x_of = lambda v: label_w + v / vmax * (W - label_w - right)
    parts = [f'<svg class="chart waterfall" viewBox="0 0 {W} {H}" role="img" aria-label="Cash-flow statement January to June 2026, {fw.replace("_", " ")}">']
    running = 0.0
    for i, (label, v, cls) in enumerate(steps):
        y = top + i * row_h
        if cls == "total":
            a, b = 0.0, v
            running = v
        else:
            a, b = running, running + v
            running = b
        x0, x1 = x_of(min(a, b)), x_of(max(a, b))
        w = max(x1 - x0, 2)
        parts.append(f'<text class="wf-label" x="{label_w - 12}" y="{y + row_h / 2 + 5:.1f}" text-anchor="end">{label}</text>')
        parts.append(f'<rect class="wf {cls}{" neg" if v < 0 else ""}" x="{x0:.1f}" y="{y + 8:.1f}" width="{w:.1f}" height="{row_h - 16}" rx="4"/>')
        val = fmt(v) if cls == "total" else fmt(v, True)
        parts.append(f'<text class="wf-val" x="{x1 + 8:.1f}" y="{y + row_h / 2 + 5:.1f}">{val}</text>')
        if i < len(steps) - 1:
            nx = x_of(running)
            parts.append(f'<line class="wf-link" x1="{nx:.1f}" x2="{nx:.1f}" y1="{y + row_h - 8:.1f}" y2="{y + row_h + 8:.1f}"/>')
    parts.append("</svg>")
    return "".join(parts)


def flow_list(fw: str = "IFRS") -> str:
    """Phones: the same story as ranked bars."""
    key = 3 if fw == "IFRS" else 4
    mx = max(v for _, v in REVENUE + [(l[0], l[2]) for l in LINES])
    def row(name, v, cls=""):
        return (f'<div class="flow-row {cls}"><span>{esc(name)}</span><span class="amt">{fmt(v)}</span>'
                f'<span class="bar"><i style="width:{v / mx * 100:.0f}%"></i></span></div>')
    ins = "".join(row(n, v) for n, v in REVENUE[:3])
    outs = "".join(row(l[1][fw], l[2], "out") for l in sorted(LINES, key=lambda l: -l[2])[:4])
    return (f'<div class="flow-list"><div><h3>Most revenue came from</h3>{ins}</div>'
            f'<div><h3>Most money went to</h3>{outs}{row("Kept in the account", KEPT, "kept")}</div></div>')
