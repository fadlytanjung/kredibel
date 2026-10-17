"""Kredibel 2.1 screen mocks (finance workspace). Each function returns the body markup.
Synthetic data: the demo workspace of docs/18 (Sunrise Coffee Roasters, Jan–Jun 2026, scenarios S1 to S4
together: the edited March statement, the duplicates, the changed supplier account and the unpaid bills)."""

import json
import re
from decimal import Decimal
from html import escape
from pathlib import Path

from icons import icon
from shell import shell, topbar, BRAND
from sankey import sankey_svg, flow_list, flow_table
import charts

SEV = {"critical": ("octagon-alert", "Critical"), "high": ("triangle-alert", "High"),
       "medium": ("circle-alert", "Medium"), "low": ("info", "Low")}


# ------------------------------------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------------------------------------
# The dashboard draws the same synthetic Dashboard payload as the React preview and the browser parity
# check (contracts/design/fixtures/dashboard.json, AC-019-2), with the app's own words from the
# locale files, so the mock and the implementation cannot drift apart silently.

ROOT = Path(__file__).resolve().parents[3]
LOCALES = ROOT / "frontend/src/shared/i18n/locales/en"
DASH = json.loads((ROOT / "contracts/design/fixtures/dashboard.json").read_text(encoding="utf-8"))
DASH_WORDS = json.loads((LOCALES / "dashboard.json").read_text(encoding="utf-8"))
EXPECT = json.loads((ROOT / "contracts/design/fixtures/expectations.json").read_text(encoding="utf-8"))
CP_FIX = json.loads((ROOT / "contracts/design/fixtures/counterparties.json").read_text(encoding="utf-8"))
CP_WORDS = json.loads((LOCALES / "counterparties.json").read_text(encoding="utf-8"))
REVIEW_WORDS = json.loads((LOCALES / "review.json").read_text(encoding="utf-8"))
RISK_WORDS = json.loads((LOCALES / "risk.json").read_text(encoding="utf-8"))

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
STATE_CLASS = {"RECONCILED": "ok", "SIGNED_OFF": "ok"}
MTAB_TINT = {"CRITICAL": " is-critical", "HIGH": " is-high", "MEDIUM": " is-open"}
KPI_ICON = {"MONEY_IN": "arrow-down-left", "MONEY_OUT": "arrow-up-right"}
KIND_ICON = {"POSSIBLE_DUPLICATE": "copy", "PROPOSED_MATCH": "link", "UNMATCHED_DOCUMENT": "file-text",
             "UNMATCHED_BANK_LINE": "bank", "LOW_CONFIDENCE_VALUE": "eye", "LEDGER_DIFFERENCE": "scale",
             "CONFIRM_TYPE": "tag", "CONFIRM_LEDGER_MAPPING": "table"}
KIND_TILE = {"POSSIBLE_DUPLICATE": "dup", "PROPOSED_MATCH": "match"}


def month_name(month: str, style: str = "longYear") -> str:
    """The app's formatMonth: 'Mar', 'March' or 'March 2026'."""
    year, number = month.split("-")
    name = MONTH_NAMES[int(number) - 1]
    if style == "short":
        return name[:3]
    if style == "long":
        return name
    return f"{name} {year}"


def amount(value: str) -> str:
    """The app's formatAmount for a whole-unit currency: digits only, the code printed once beside it."""
    return f"{Decimal(value):,.0f}"


def words(table: dict, key: str, **params) -> str:
    """A locale string with its {{params}} filled; `count` picks the _one/_other form."""
    count = params.get("count")
    parts = key.split(".")
    node: dict = table
    for part in parts[:-1]:
        node = node[part]
    last = parts[-1]
    if count is not None and f"{last}_one" in node:
        last = f"{last}_one" if count == 1 else f"{last}_other"
    text = str(node[last])
    for name, value in params.items():
        text = text.replace("{{" + name + "}}", str(value))
    return escape(text)


def period_range(months: list[str]) -> str:
    first, last = months[0], months[-1]
    if first == last:
        return month_name(first)
    same_year = first[:4] == last[:4]
    return words(DASH_WORDS, "periodRange", first=month_name(first, "long" if same_year else "longYear"), last=month_name(last))


def sev_badge(level: str) -> str:
    ic, label = SEV[level.lower()]
    return f'<span class="badge badge-{level.lower()}">{icon(ic)}{escape(RISK_WORDS["severity"].get(level.upper(), label))}</span>'


def month_tabs() -> str:
    """The MonthStrip: one binder tab per month of the fixture (docs/12 §6.2)."""
    out = []
    for m in DASH["months"]:
        done = m["state"] in STATE_CLASS
        rate = round(float(m["autoMatchRate"]) * 100) if m.get("autoMatchRate") else None
        matched = (f'<span><b>{rate}%</b> {words(DASH_WORDS, "matchedShare")}</span><span class="meter-bar"><i style="width:{rate}%"></i></span>'
                   if rate is not None else "")
        statements = words(DASH_WORDS, "statements", present=m.get("statementsPresent", 0), expected=m.get("statementsExpected", 0))
        foot = sev_badge(m["riskLevel"]) if m.get("riskLevel") else f'<span>{words(DASH_WORDS, "noRisk")}</span>'
        out.append(f"""<li><a class="mtab{MTAB_TINT.get(m.get("riskLevel", ""), "")}" href="month.html">
  <span class="m-name"><strong>{month_name(m["month"], "short")}</strong><span>{m["month"][:4]}</span></span>
  <span class="m-state {"ok" if done else "wait"}">{icon("check-circle" if done else "inbox")}{words(DASH_WORDS, f"states.{m['state']}")}</span>
  <span class="m-matched">{matched}<span>{statements}</span></span>
  <span class="m-foot">{foot}</span>
</a></li>""")
    return f'<div class="months-wrap"><ol class="months">{"".join(out)}</ol></div>'


def seg(group: str, options: list[tuple[str, str]], active: str, label: str, touch: bool = False) -> str:
    """Segmented control; proto.js switches the panels with the same group."""
    btns = "".join(f'<button type="button" data-group="{group}" data-value="{v}" aria-pressed="{str(v == active).lower()}">{t}</button>'
                   for v, t in options)
    return f'<div class="seg{" seg-touch" if touch else ""}" role="group" aria-label="{label}">{btns}</div>'


def tiers(wide: str, medium: str, compact: str) -> str:
    """The same chart drawn for wide panels (960 px and up), medium ones (640 to 959) and phones."""
    return f'<div class="chart-wide">{wide}</div><div class="chart-medium">{medium}</div><div class="chart-compact">{compact}</div>'


def by_fw(render) -> str:
    """The same chart for IFRS (shown) and US GAAP (hidden until the framework switch)."""
    return (f'<div data-show-group="fw" data-show-value="IFRS">{render("IFRS")}</div>'
            f'<div data-show-group="fw" data-show-value="US_GAAP" hidden>{render("US_GAAP")}</div>')


from profit_loss import panel as profit_loss_panel, page as profit_loss


def kpi_figure(kpi: dict) -> str:
    """One KpiCard: the figure, its note and, for the match rate, the small meter."""
    kid, value, previous = kpi["id"], kpi["value"], kpi.get("previous")
    label = words(DASH_WORDS, f"kpi.{kid}")
    ic = f'{icon(KPI_ICON[kid], "icon icon-sm")}' if kid in KPI_ICON else ""
    attn = ""
    extra = ""
    if isinstance(value, dict):
        sign = "+" if kid == "NET" and not value["amount"].startswith("-") and value["amount"] != "0.00" else ""
        shown = f'<small>{value["currency"]}</small>{sign}{amount(value["amount"])}'
        if kid == "NET":
            up = not value["amount"].startswith("-")
            note = f'<dd class="n{" up" if up else ""}">{words(DASH_WORDS, "kept" if up else "taken")}</dd>'
        else:
            note = f'<dd class="n">{words(DASH_WORDS, "previous", value=amount(previous["amount"])) if previous else words(DASH_WORDS, "noPrevious")}</dd>'
    elif kid == "AUTO_MATCH_RATE":
        pct = lambda rate: f"{round(float(rate) * 1000) / 10:.1f}%"  # noqa: E731
        shown = pct(value)
        note = f'<dd class="n">{words(DASH_WORDS, "previous", value=pct(previous)) if previous else words(DASH_WORDS, "noPrevious")}</dd>'
        extra = f'<dd class="mini"><i style="width:{pct(value)}"></i></dd>'
    else:
        count = int(value)
        shown = str(count)
        attn = ' class="is-attn"' if count > 0 else ""
        if kid == "DOCUMENTS_WAITING":
            note = (f'<dd class="n"><a class="link" href="documents.html">{words(DASH_WORDS, "documentsWaiting", count=count)}</a></dd>'
                    if count else f'<dd class="n">{words(DASH_WORDS, "nothingWaiting")}</dd>')
        else:
            note = (f'<dd class="n"><a class="link" href="review.html">{words(DASH_WORDS, "reviewWaiting", count=count)}</a></dd>'
                    if count else f'<dd class="n">{words(DASH_WORDS, "nothingToReview")}</dd>')
    return f'<div{attn}><dt>{ic}{label}</dt><dd class="v">{shown}</dd>{note}{extra}</div>'


def flow_rows(nodes: list[dict], maximum: Decimal, out: bool = False) -> str:
    rows = []
    for node in nodes:
        value = Decimal(node["value"]["amount"])
        width = f"{(value / maximum * 100):.1f}%" if maximum > 0 else "0%"
        rows.append(f'<div class="flow-row{" out" if out else ""}"><span>{escape(node["label"])}</span>'
                    f'<span class="amt">{amount(node["value"]["amount"])}</span><span class="bar"><i style="width:{width}"></i></span></div>')
    return "".join(rows)


DASH_TODAY = "2026-06"  # the mock's today; the browser check fixes the clock to the same month


def _month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def _month_at(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def period_picker(first: str, last: str, today: str) -> str:
    """The dashboard's period as widgets/dashboard/PeriodPicker.tsx draws a range: Month, Range or
    Year, then the first and last month (at most 12), nothing after today."""
    data = sorted(m["month"] for m in DASH["months"])
    top = max(_month_index(today), _month_index(data[-1]))
    bottom = min(_month_index(today) - 23, _month_index(data[0]))
    months = [_month_at(i) for i in range(top, bottom - 1, -1)]
    to_months = [m for m in months if 0 <= _month_index(m) - _month_index(first) < 12]

    def options(items: list[str], chosen: str) -> str:
        return "".join(f'<option value="{m}"{" selected" if m == chosen else ""}>{month_name(m)}</option>' for m in items)

    kinds = seg("periodkind", [(k, words(DASH_WORDS, f"periods.kinds.{k}")) for k in ("month", "range", "year")], "range", words(DASH_WORDS, "periods.label"))
    return (f'<div class="period-picker">{kinds}<div class="period-fields">'
            f'<select class="select select-sm" aria-label="{words(DASH_WORDS, "periods.from")}">{options(months, first)}</select>'
            f'<span class="muted small">{words(DASH_WORDS, "periods.to")}</span>'
            f'<select class="select select-sm" aria-label="{words(DASH_WORDS, "periods.toLabel")}">{options(to_months, last)}</select>'
            f'</div><span class="muted small period-hint">{words(DASH_WORDS, "periods.rangeHint", count=12)}</span></div>')


def expectations_panel(currency: str = "IDR") -> str:
    """Spec 024: what the person expected against the reconciled months (ExpectationsPanel)."""
    status_icon = {"AS_EXPECTED": "check-circle", "DIFFERENT": "scale", "WAITING": "clock"}
    status_class = {"AS_EXPECTED": "ok", "DIFFERENT": "wait", "WAITING": "busy"}

    def side(label: str, s: dict) -> str:
        if s["status"] == "DIFFERENT":
            diff = s["difference"]
            key = "DIFFERENT_less" if diff.startswith("-") else "DIFFERENT_more"
            status = words(DASH_WORDS, f"expectations.status.{key}", difference=amount(diff.lstrip("-")))
        else:
            status = words(DASH_WORDS, f"expectations.status.{s['status']}")
        found = (f'<span>{words(DASH_WORDS, "expectations.found")} <strong>{amount(s["actual"])}</strong></span>'
                 if s["actual"] is not None else "")
        return (f'<div class="expect-side"><span class="k">{label}</span><span class="v">'
                f'<span>{words(DASH_WORDS, "expectations.expected")} <strong>{amount(s["expected"])}</strong></span>{found}</span>'
                f'<span class="status-line {status_class[s["status"]]}">{icon(status_icon[s["status"]], "icon icon-sm")}{status}</span></div>')

    items = ""
    for m in EXPECT["months"]:
        sides = "".join(side(words(DASH_WORDS, f"expectations.{k}"), m[k]) for k in ("moneyIn", "moneyOut") if m.get(k))
        items += (f'<li><div class="expect-month"><h3>{month_name(m["month"])}</h3><div class="expect-links">'
                  f'<a class="button button-secondary button-sm" href="month.html">{words(DASH_WORDS, "expectations.openMonth")}</a>'
                  f'<a class="button button-quiet button-sm" href="transactions.html">{icon("table", "icon icon-sm")}{words(DASH_WORDS, "expectations.transactions")}</a>'
                  f'<a class="button button-quiet button-sm" href="documents.html">{icon("files", "icon icon-sm")}{words(DASH_WORDS, "expectations.documents")}</a>'
                  f'</div></div><div class="expect-sides">{sides}</div></li>')
    tolerance = round(float(EXPECT["tolerance"]) * 100)
    return f"""
<section class="panel" aria-labelledby="dash-expect-h">
  <div class="panel-head"><div class="stack gap-1"><h2 id="dash-expect-h">{words(DASH_WORDS, "expectations.title")}</h2><p class="small muted">{words(DASH_WORDS, "expectations.subtitle", currency=currency, tolerance=tolerance)}</p></div><a class="link" href="welcome-expect.html">{words(DASH_WORDS, "expectations.change")}</a></div>
  <ul class="expect-list">{items}</ul>
</section>"""


def suggestion_card(place: str) -> str:
    """Profile suggestions (SuggestionCard, spec 014): what was found, where (a link to the document)
    and a decision. On the dashboard a link to Profile settings, the card's home."""
    items = "".join(
        f'<li class="suggestion"><span class="kind doc">{icon("lightbulb", "icon icon-sm")}</span>'
        f'<span><p class="a-t">{words(CP_WORDS, f"suggestions.fields.{s["field"]}")}: {escape(s["display"])}</p>'
        f'<p class="a-s">{words(CP_WORDS, f"suggestions.confidence.{s["confidence"]}")}, '
        f'<a href="document.html">{words(CP_WORDS, "suggestions.evidence", count=len(s["evidence"]))}</a></p></span>'
        f'<span class="actions"><button type="button" class="button button-primary button-sm">{words(CP_WORDS, "suggestions.accept")}</button>'
        f'<button type="button" class="button button-quiet button-sm">{words(CP_WORDS, "suggestions.reject")}</button></span></li>'
        for s in CP_FIX["suggestions"])
    home = f'<a class="link" href="settings-profile.html">{words(CP_WORDS, "suggestions.settings")}</a>' if place == "dashboard" else ""
    return f"""
  <section class="panel" aria-labelledby="dash-suggest-h">
    <div class="panel-head"><h2 id="dash-suggest-h">{words(CP_WORDS, "suggestions.title")}</h2>{home}</div>
    <p class="small muted panel-pad">{words(CP_WORDS, "suggestions.found", count=len(CP_FIX["suggestions"]))}</p>
    <ul class="alert-list">{items}</ul>
  </section>"""


def dashboard(extra: str = "", expectations: bool = False) -> str:
    """The dashboard as the app draws it (DashboardPage, docs/11 §6.2): period, header, figures, the
    P&L panel, where the money went, reconciliation and findings, three panels, the months. The
    profile-suggestions card at the end is a planned design (spec 014)."""
    months = DASH["periodMonths"]
    period = period_range(months)
    name = "Sunrise Coffee Roasters"
    in_period = [m for m in DASH["months"] if m["month"] in months]
    done = sum(1 for m in in_period if m["state"] in STATE_CLASS)
    alerts = DASH["alerts"]
    worst = sorted((m for m in in_period if m.get("riskLevel")),
                   key=lambda m: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(m["riskLevel"]))[0]
    why = [a for a in alerts if a["severity"] in ("CRITICAL", "HIGH")][:2]

    period_row = f'<div class="dash-period">{period_picker(months[0], months[-1], DASH_TODAY)}</div>'
    header = f'<header class="stack gap-1"><h1 class="type-title">{name}</h1><p class="greeting muted">{words(DASH_WORDS, "greeting", name=name, range=period)}</p></header>'
    figs = f"""
<section class="ledger" aria-label="{words(DASH_WORDS, "figuresAria", range=period)}">
  <dl class="ledger-figures">{"".join(kpi_figure(k) for k in DASH["kpis"])}</dl>
</section>"""

    flow_views = seg("flowview", [(k, words(DASH_WORDS, f"charts.views.{k}")) for k in ("flow", "bars", "table", "parties")], "flow", words(DASH_WORDS, "charts.viewLabel"))
    fw_note = ('<p class="chart-note" data-text-group="fw" '
               'data-text-ifrs="Amounts in millions. IFRS: interest paid (12.0) is a financing cash flow, as IAS 7 classifies it after IFRS 18; applied to 2026 for comparability." '
               'data-text-us_gaap="Amounts in millions. US GAAP: interest paid (12.0) is an operating cash flow (ASC 230), so operating activities are larger and financing smaller.">'
               'Amounts in millions. IFRS: interest paid (12.0) is a financing cash flow, as IAS 7 classifies it after IFRS 18; applied to 2026 for comparability.</p>')
    flow = f"""
<article class="chart-panel" aria-labelledby="money-flow-h">
  <div class="chart-head">
    <div><h3 id="money-flow-h">{words(DASH_WORDS, "charts.flowTitle")}</h3><p>{words(DASH_WORDS, "charts.flowSubtitle.flow")}</p></div>
    {flow_views}
  </div>
  <div data-show-group="flowview" data-show-value="flow">
    {tiers(by_fw(charts.statement_sankey), by_fw(lambda fw: charts.statement_sankey(fw, 860)), by_fw(charts.flow_list))}
  </div>
  <div data-show-group="flowview" data-show-value="bars" hidden>{by_fw(charts.spend_bars)}</div>
  <div data-show-group="flowview" data-show-value="table" hidden>{by_fw(charts.flow_table)}</div>
  <div data-show-group="flowview" data-show-value="parties" hidden><div class="chart-roomy">{sankey_svg()}</div><div class="chart-compact">{flow_list()}</div></div>
  <div class="chart-foot">{fw_note}</div>
</article>"""
    hot = ", ".join(month_name(m["month"]) for m in in_period if m.get("riskLevel") in ("CRITICAL", "HIGH"))
    monthly = f"""
<article class="chart-panel" aria-labelledby="month-bars-h">
  <div class="chart-head">
    <div><h3 id="month-bars-h">{words(DASH_WORDS, "charts.monthsTitle")}</h3><p>{words(DASH_WORDS, "charts.monthsSubtitleHot", months=hot) if hot else words(DASH_WORDS, "charts.monthsSubtitle")}</p></div>
    {seg("monthview", [("inout", words(DASH_WORDS, "charts.inOut")), ("net", words(DASH_WORDS, "charts.netBalance"))], "inout", words(DASH_WORDS, "charts.monthsViewLabel"))}
  </div>
  <div data-show-group="monthview" data-show-value="inout">
    {tiers(charts.monthly_bars(), charts.monthly_bars(medium=True), charts.monthly_bars(compact=True))}
    <p class="chart-legend"><span class="in"><i></i>{words(DASH_WORDS, "charts.moneyIn")}</span><span class="out"><i></i>{words(DASH_WORDS, "charts.moneyOut")}</span></p>
  </div>
  <div data-show-group="monthview" data-show-value="net" hidden>
    {tiers(charts.net_bars(), charts.net_bars(medium=True), charts.net_bars(compact=True))}
    <p class="chart-legend"><span class="net"><i></i>{words(DASH_WORDS, "charts.net")}</span><span class="bal"><i></i>{words(DASH_WORDS, "charts.balance")}</span></p>
  </div>
</article>"""
    statement = f"""
<article class="chart-panel" aria-labelledby="waterfall-h">
  <div class="chart-head">
    <div><h3 id="waterfall-h">{words(DASH_WORDS, "charts.waterfallTitle")}</h3><p data-text-group="fw" data-text-ifrs="{words(DASH_WORDS, "charts.waterfallSubtitle", framework="IFRS")}" data-text-us_gaap="{words(DASH_WORDS, "charts.waterfallSubtitle", framework="US GAAP")}">{words(DASH_WORDS, "charts.waterfallSubtitle", framework="IFRS")}</p></div>
    <a class="link" href="month.html">{icon("table", "icon icon-sm")}{words(DASH_WORDS, "charts.byMonth")}</a>
  </div>
  {tiers(by_fw(charts.waterfall), by_fw(lambda fw: charts.waterfall(fw, medium=True)), by_fw(lambda fw: charts.waterfall(fw, compact=True)))}
</article>"""
    charts_section = f"""
<section class="stack gap-4" aria-labelledby="charts-h">
  <div class="section-head charts-section-head">
    <div><h2 class="type-h2" id="charts-h">{words(DASH_WORDS, "charts.title")}</h2><p>{words(DASH_WORDS, "charts.subtitle", range=period)}</p></div>
    <span class="fw-switch">{words(DASH_WORDS, "charts.framework")}{seg("fw", [("IFRS", "IFRS"), ("US_GAAP", "US GAAP")], "IFRS", words(DASH_WORDS, "charts.framework"))}</span>
  </div>
  <div class="charts">
    {flow}
    {monthly}
    {statement}
  </div>
</section>"""

    why_items = "".join(
        f'<li><span class="sev-{a["severity"].lower()}">{icon("octagon-alert" if a["severity"] == "CRITICAL" else "triangle-alert")}</span>'
        f'<span><strong>{month_name(a["month"], "long")}: </strong>{escape(a["title"])}</span></li>' for a in why)
    status = (f'<span class="done">{words(DASH_WORDS, "reconciled", done=done, count=len(in_period))}</span> '
              f'<span class="ask">{words(DASH_WORDS, "openFindings", count=len(alerts)) if alerts else words(DASH_WORDS, "nothingOpen")}</span>')
    hero = f"""
<section class="status-hero" aria-labelledby="status-h">
  <div class="section-head">
    <h2 class="type-h2" id="status-h">{words(DASH_WORDS, "reconciliationHealth")}</h2>
    <div class="actions">
      <a class="button button-secondary button-sm" href="month.html">{words(DASH_WORDS, "seeMonth", month=month_name(worst["month"], "long"))}</a>
      <a class="button button-quiet button-sm" href="assistant.html">{icon("sparkles", "icon icon-sm")}{words(DASH_WORDS, "askAboutThis")}</a>
    </div>
  </div>
  <p class="status-sentence">{status}</p>
  <ul class="why">{why_items}</ul>
</section>"""

    risk_items = "".join(
        f'<li><a href="evidence-viewer.html"><span class="sev">{sev_badge(a["severity"])}</span>'
        f'<span><p class="a-t">{escape(a["title"])}</p><p class="a-s">{month_name(a["month"])}</p></span></a></li>' for a in alerts)
    review_items = "".join(
        f'<li><a href="review.html"><span class="kind {KIND_TILE.get(i["kind"], "doc")}">{icon(KIND_ICON.get(i["kind"], "inbox"), "icon icon-sm")}</span>'
        f'<span><p class="a-t">{escape(i["title"])}</p><p class="a-s">{words(REVIEW_WORDS, f"kinds.{i['kind']}")}, {month_name(i["month"])}</p></span></a></li>'
        for i in DASH["reviewPreview"])
    summary = DASH["moneyFlowSummary"]
    maximum = max(Decimal(n["value"]["amount"]) for n in summary["topSources"] + summary["topUses"])
    lists = f"""
<div class="dash-lists">
  <section class="panel" aria-labelledby="dash-risk-h">
    <div class="panel-head"><h2 id="dash-risk-h">{words(DASH_WORDS, "risk")}</h2><a class="link" href="risk.html">{words(DASH_WORDS, "allFindings")}</a></div>
    <ul class="alert-list">{risk_items}</ul>
  </section>
  <section class="panel" aria-labelledby="dash-review-h">
    <div class="panel-head"><h2 id="dash-review-h">{words(DASH_WORDS, "review")}</h2><a class="link" href="review.html">{words(DASH_WORDS, "allReview")}</a></div>
    <ul class="alert-list">{review_items}</ul>
  </section>
  {suggestion_card("dashboard")}
  <section class="panel" aria-labelledby="dash-flow-h">
    <div class="panel-head"><h2 id="dash-flow-h">{words(DASH_WORDS, "flowTitle")}</h2></div>
    <div class="stack gap-4 panel-pad">
      <div><h3 class="small muted">{words(DASH_WORDS, "flowIn")}</h3>{flow_rows(summary["topSources"], maximum)}</div>
      <div><h3 class="small muted">{words(DASH_WORDS, "flowOut")}</h3>{flow_rows(summary["topUses"], maximum, out=True)}</div>
    </div>
  </section>
</div>"""
    months_section = f"""
<section aria-labelledby="months-h">
  <div class="section-head"><h2 class="type-h2" id="months-h">{words(DASH_WORDS, "monthsTitle")}</h2><a class="link" href="month.html">{words(DASH_WORDS, "reconciliation")}</a></div>
  {month_tabs()}
</section>"""
    found = f"""
<section class="found" aria-label="Profile suggestions (planned, spec 014)">
  {icon("sparkles", "icon icon-lg")}
  <p><span class="badge badge-outline">Planned, spec 014</span> <strong>Kredibel found 2 details for your profile:</strong> your tax ID and your address, both printed on your sales invoices. Nothing changes until you accept.</p>
  <a class="button button-secondary" href="plan-usage.html">Review details</a>
</section>"""
    content = f"""
<div class="page">
  {period_row}
  <div class="dash">
    {header}
    {figs}{expectations_panel() if expectations else ""}
    {profit_loss_panel()}
    {charts_section}
    {hero}
    {lists}
    {months_section}
    {found}
  </div>
</div>{extra}"""
    return shell("dashboard", topbar("Dashboard", ("Dashboard",)), content)


TOUR_WORDS = json.loads((LOCALES / "tour.json").read_text(encoding="utf-8"))
TOUR_IDS = ["welcome", "period", "figures", "flow", "upload", "months", "transactions", "review", "risk", "labels", "runs", "assistant", "done"]

# The same placement as features/tour/position.ts, measured in the browser like the app.
TOUR_SCRIPT = """<script>
(function () {
  var part = document.querySelector('#content .dash .ledger');
  var spot = document.querySelector('.tour-spot');
  var card = document.querySelector('.tour-card');
  function place() {
    var vw = window.innerWidth, vh = window.innerHeight;
    var r = part.getBoundingClientRect();
    var top = Math.max(r.top - 8, 0), left = Math.max(r.left - 8, 0);
    var bottom = Math.min(r.top + r.height + 8, vh), right = Math.min(r.left + r.width + 8, vw);
    spot.style.top = top + 'px'; spot.style.left = left + 'px';
    spot.style.width = Math.max(right - left, 0) + 'px'; spot.style.height = Math.max(bottom - top, 0) + 'px';
    var c = card.getBoundingClientRect();
    var t, l;
    if (vw < 600) { t = vh - c.height - 16; l = 16; }
    else {
      var clamp = function (x) { return Math.min(Math.max(x, 16), vw - c.width - 16); };
      var below = bottom + 12;
      if (below + c.height + 16 <= vh) { t = below; } else if (top - 12 - c.height >= 16) { t = top - 12 - c.height; } else { t = Math.max(vh - c.height - 16, 16); }
      l = clamp(left);
    }
    card.style.top = t + 'px'; card.style.left = l + 'px'; card.classList.remove('is-measuring');
  }
  if (window.innerWidth < 600) window.scrollTo({ top: window.scrollY + part.getBoundingClientRect().top - 72 });
  else part.scrollIntoView({ block: 'center' });
  place();
  window.addEventListener('scroll', place, true);
  window.addEventListener('resize', place);
})();
</script>"""


def tour_overlay(step_id: str = "figures") -> str:
    """One step of the guided tour as features/tour/TourOverlay.tsx draws it (spec 021)."""
    n = TOUR_IDS.index(step_id) + 1
    tw = lambda key, **kw: words(TOUR_WORDS, key, **kw)  # noqa: E731
    return f"""
<div class="tour">
  <div class="tour-catch" aria-hidden="true"></div>
  <div class="tour-spot" aria-hidden="true"></div>
  <section class="tour-card is-measuring" role="dialog" aria-modal="true" aria-labelledby="tour-h" aria-describedby="tour-p">
    <p class="tour-step">{tw("stepOf", n=n, total=len(TOUR_IDS))}</p>
    <h2 id="tour-h" tabindex="-1">{tw(f"steps.{step_id}.title", name="Sunrise Coffee Roasters")}</h2>
    <p id="tour-p">{tw(f"steps.{step_id}.body")}</p>
    <div class="tour-actions"><button type="button" class="button button-quiet button-sm">{tw("skip")}</button><span class="tour-grow"></span><button type="button" class="button button-secondary button-sm">{icon("chevron-left", "icon icon-sm")}{tw("back")}</button><button type="button" class="button button-primary button-sm">{tw("next")}{icon("chevron-right", "icon icon-sm")}</button></div>
  </section>
</div>{TOUR_SCRIPT}"""


def tour() -> str:
    return dashboard(extra=tour_overlay("figures"))

# ------------------------------------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------------------------------------

UPLOADS_FIX = json.loads((ROOT / "contracts/design/fixtures/documents.json").read_text(encoding="utf-8"))
TRAY_ICON = {"uploading": "refresh", "reading": "refresh", "copy": "copy", "held": "copy", "columns": "table",
             "needsInput": "triangle-alert", "failed": "triangle-alert", "error": "triangle-alert", "done": "file-text"}
TRAY_TONE = {"uploading": "is-busy", "reading": "is-busy", "copy": "is-dup", "held": "is-held"}
BUSY_STATES = ("UPLOADED", "SCREENING", "READING", "CHECKING")


def _ts_of(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def tray_row(doc: dict, by_id: dict, items: list[dict]) -> dict:
    """As features/upload/trayRows.ts rowOf: the state of one upload and its next step."""
    base = {"key": doc["docId"], "fileName": doc["fileName"], "docId": doc["docId"], "docType": doc.get("docType")}
    dup = doc.get("duplicate") or {}
    original = by_id.get(dup.get("ofDocId"))
    if doc["status"] == "DUPLICATE":
        return {**base, "state": "copy", "original": original}
    if doc.get("heldAsDuplicate"):
        return {**base, "state": "held", "original": original, "reasonCode": dup.get("code"), "reviewItemId": dup.get("reviewItemId")}
    if doc.get("docType") == "LEDGER_EXPORT" and (doc.get("ledgerMeta") or {}).get("mappingStatus") == "PROPOSED":
        item = next((i for i in items if i["kind"] == "CONFIRM_LEDGER_MAPPING" and i.get("docId") == doc["docId"]), None)
        return {**base, "state": "columns", "reviewItemId": item and item["itemId"]}
    if doc["status"] in BUSY_STATES:
        pages = doc.get("pageCount") or len(doc.get("pages") or [])
        done = sum(1 for pg in doc.get("pages") or [] if pg["status"] in ("DONE", "BLANK"))
        progress = round((min(done, pages - 1) + 0.5) / pages * 100) if pages else None
        return {**base, "state": "reading", "page": min(done + 1, pages) if pages else None, "pages": pages, "progress": progress}
    if doc["status"] == "NEEDS_INPUT":
        return {**base, "state": "needsInput", "detail": doc.get("statusDetail")}
    if doc["status"] in ("FAILED", "QUARANTINED"):
        return {**base, "state": "failed", "detail": doc.get("statusDetail")}
    meta = doc.get("ledgerMeta") or {}
    return {**base, "state": "done", "rows": meta.get("rowsImported") or meta.get("rows")}


def tray_rows(docs: list[dict], items: list[dict], now: str) -> list[dict]:
    """As trayRows.ts: the last day and anything waiting for a person, newest first, at most 6."""
    by_id = {d["docId"]: d for d in docs}

    def needs(d: dict) -> bool:
        return bool(d.get("heldAsDuplicate")) or (d.get("docType") == "LEDGER_EXPORT" and (d.get("ledgerMeta") or {}).get("mappingStatus") == "PROPOSED") or d["status"] in ("NEEDS_INPUT", "FAILED")

    recent = [d for d in docs if needs(d) or _ts_of(now) - _ts_of(d["uploadedAt"]) < 86400]
    recent.sort(key=lambda d: _ts_of(d["uploadedAt"]), reverse=True)
    return [tray_row(d, by_id, items) for d in recent][:6]


def tray_message(row: dict) -> str:
    dw = lambda key, **kw: words(DOC_WORDS, key, **kw)  # noqa: E731
    orig = row.get("original")
    link = (f'<a href="document.html">{escape(orig["fileName"])}</a>' if orig else dw("upload.anEarlierFile"))

    def tagged(key: str, **kw) -> str:
        """The sentence with its <original> part as a link to the earlier file, as <Trans> does."""
        text = dw(key, **kw).replace("&lt;original&gt;", "<original>").replace("&lt;/original&gt;", "</original>")
        if "<original>" not in text:
            return text
        before, rest = text.split("<original>", 1)
        return before + link + rest.split("</original>", 1)[1]

    state = row["state"]
    if state == "reading":
        if row.get("page") and row.get("pages"):
            return f'{dw("upload.readingPage", page=row["page"], total=row["pages"])}<span class="pbar"><i style="width:{row["progress"]}%"></i></span>'
        return dw("upload.readingFile")
    if state == "copy":
        day = ""
        if orig:
            year, month, rest = orig["uploadedAt"][:10].split("-")
            day = f"{int(rest)} {MONTH_NAMES[int(month) - 1][:3]}"
        return tagged("upload.copyNotice", date=day, name=orig["fileName"] if orig else "")
    if state == "held":
        reason = (DOC_WORDS["upload"].get("heldReasons") or {}).get(row.get("reasonCode") or "", "")
        if reason:
            return tagged("upload.heldNotice", name=orig["fileName"] if orig else "", reason=reason)
        return tagged("upload.heldNoticePlain", name=orig["fileName"] if orig else "")
    if state == "columns":
        return dw("upload.columnsNotice")
    if state == "needsInput":
        return escape(row.get("detail") or dw("status.needsInput"))
    if state == "failed":
        return f'<span class="text-danger">{escape(row.get("detail") or dw("upload.failed"))}</span>'
    if row.get("rows"):
        return dw("upload.rowsImported", count=row["rows"])
    return dw("upload.read", type=dw(f"detail.docType.{row.get('docType')}"))


def tray_action(row: dict) -> str:
    dw = lambda key: words(DOC_WORDS, key)  # noqa: E731
    if row["state"] == "held":
        return f'<span class="act"><a class="button button-secondary button-sm" href="review-correction.html">{dw("upload.decide")}</a></span>'
    if row["state"] == "columns":
        return f'<span class="act"><a class="button button-primary button-sm" href="review-mapping.html">{dw("upload.checkColumns")}</a></span>'
    if row["state"] == "needsInput":
        return f'<span class="act"><a class="button button-secondary button-sm" href="review.html">{dw("upload.review")}</a></span>'
    if row["state"] == "done":
        return f'<span class="act"><a class="button button-quiet button-sm" href="document.html">{dw("upload.open")}</a></span>'
    return ""


def upload_tray() -> str:
    """The upload tray as features/upload/UploadSheet.tsx draws it, from documents.json."""
    dw = lambda key: words(DOC_WORDS, key)  # noqa: E731
    rows = tray_rows(UPLOADS_FIX["items"], UPLOADS_FIX["reviewItems"], UPLOADS_FIX["now"])
    lis = "".join(
        f'<li><span class="{" ".join(c for c in ("file-ico", TRAY_TONE.get(r["state"], "")) if c)}">{icon("table" if r["state"] == "done" and r.get("docType") == "LEDGER_EXPORT" else TRAY_ICON[r["state"]])}</span>'
        f'<span class="f">{escape(r["fileName"])}</span><span class="m{" is-dup" if r["state"] == "copy" else ""}">{tray_message(r)}</span>{tray_action(r)}</li>'
        for r in rows)
    return f"""
<section class="tray" aria-labelledby="tray-h">
  <div class="tray-drop">
    <span class="ico">{icon("upload")}</span>
    <p><strong id="tray-h">{dw("upload.title")}</strong>{dw("upload.description")}</p>
    <a class="button button-primary" href="#">{icon("plus", "icon icon-sm")}{dw("upload.chooseFiles")}</a>
    <a class="button button-secondary only-compact" href="#">{icon("camera", "icon icon-sm")}{dw("upload.takePhoto")}</a>
  </div>
  <ul class="tray-list" aria-label="{dw("upload.justUploaded")}">{lis}</ul>
</section>"""


def documents() -> str:
    tray = upload_tray()
    chips = "".join(
        f'<a class="chip" href="#"{" aria-pressed=\"true\"" if i == 0 else ""}>{label} <span class="n">{n}</span></a>'
        for i, (label, n) in enumerate([("All", 92), ("Statements", 7), ("Sales invoices", 24), ("Purchase invoices", 18),
                                        ("Receipts", 26), ("Ledger", 1), ("Possible copies", 3)]))
    rows = [
        ("file-text", "", "ACB_Mar_2026.pdf", "Bank statement, 1 to 31 Mar, 3 pages", ("ok", "check-circle", "Read"), '<span class="badge badge-tampered">' + icon("shield-x") + 'Edited</span>', "critical", "Mar", "2 Jul", True),
        ("table", " is-sheet", "ledger-2026-H1.csv", "Ledger export, 1,184 rows, Jan to Jun", ("ok", "check-circle", "Imported"), '<span class="muted small">No pages to check</span>', "low", "Jan to Jun", "2 Jul", False),
        ("file-text", "", "RES-0045.pdf", "Purchase invoice, Roastline Equipment Service", ("ok", "check-circle", "Read"), '<span class="badge badge-clean">' + icon("shield-check") + 'Clean</span>', "high", "May", "8 Jul", False),
        ("copy", "", "ACB_Feb_2026 (re-download).pdf", "Bank statement, 1 to 29 Feb, possible copy", ("wait", "copy", "Held"), '<span class="badge badge-clean">' + icon("shield-check") + 'Clean</span>', "medium", "Feb", "9 Jul", False),
        ("file-text", "", "BLU-2026-118.pdf", "Purchase invoice, Bluewater Trading Co.", ("ok", "check-circle", "Read"), '<span class="badge badge-clean">' + icon("shield-check") + 'Clean</span>', "medium", "May", "9 Jul", False),
        ("receipt", "", "Receipt 0617.jpg", "Receipt, Cendana Fuel Station, photo", ("ok", "check-circle", "Read"), '<span class="badge badge-clean">' + icon("shield-check") + 'Clean</span>', "low", "Jun", "10 Jul", False),
        ("file-text", "", "INV-SCR-2026-06-0024.pdf", "Sales invoice, Daybreak Café, due 25 Jul", ("ok", "check-circle", "Read"), '<span class="badge badge-clean">' + icon("shield-check") + 'Clean</span>', "low", "Jun", "10 Jul", False),
        ("file-text", "", "ACB_Jun_2026.pdf", "Bank statement, 1 to 30 Jun, 3 pages", ("busy", "refresh", "Page 2 of 3"), '<span class="muted small">After reading</span>', None, "Jun", "Today", False),
    ]
    trs = []
    for ic, thumb_cls, name, sub, (st, sti, stl), check, risk, months, when, flagged in rows:
        risk_html = sev_badge(risk) if risk else '<span class="muted small">Not yet</span>'
        trs.append(f"""<tr{' class="is-flagged"' if flagged else ''}>
  <td><span class="doc-cell"><span class="thumb{thumb_cls}">{icon(ic)}</span><span><a class="doc-link" href="{"evidence-viewer.html" if flagged else "labels.html"}"><strong>{name}</strong></a><span class="sub">{sub}</span></span></span></td>
  <td class="r only-rt" data-cell="wide">{risk_html}<span class="status-line {st}">{icon(sti)}{stl}</span></td>
  <td class="hide-rt" data-cell="hide"><span class="status-line {st}">{icon(sti)}{stl}</span></td>
  <td class="hide-rt" data-cell="hide">{check}</td>
  <td class="hide-rt" data-cell="hide">{risk_html}</td>
  <td class="hide-rt" data-cell="hide">{months}</td>
  <td class="r hide-rt" data-cell="hide">{when}</td>
</tr>""")
    table = f"""
<div class="table-panel rt-wrap">
  <table class="data-table rt">
    <thead><tr><th>Document</th><th class="only-rt"></th><th>Status</th><th>Check</th><th>Risk</th><th>Months</th><th class="r">Uploaded</th></tr></thead>
    <tbody>{''.join(trs)}</tbody>
  </table>
</div>"""
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">Documents</h1>
    <p>Everything you uploaded, in any order. Kredibel reads each file twice and checks it before its numbers count.</p>
  </div>
  <div class="stack gap-6">
    {tray}
    <div class="stack gap-3">
      <div class="spread"><div class="chips" role="group" aria-label="Filter by type">{chips}</div></div>
      {table}
      <p class="muted small">Showing 8 of 92. Possible copies stay out of your figures until you decide.</p>
    </div>
  </div>
</div>"""
    return shell("documents", topbar("Documents", ("Documents",)), content)


# ------------------------------------------------------------------------------------------------
# Reconciliation evidence states (a separate synthetic MYR workspace preview)
# ------------------------------------------------------------------------------------------------

def reconciliation() -> str:
    bank_rows = [
        ("6 Jul", "Daybreak Café", "+1,500.00", "Matched to 2 invoices", "auto", "link",
         "INV-101: MYR 600.00; INV-102: MYR 900.00. Remaining difference: MYR 0.00.",
         "Same client; both invoice references in the transfer; paid within both date windows."),
        ("8 and 10 Jul", "Harborview Hotel Group", "+800.00", "Paid in 2 transfers", "auto", "link",
         "INV-103: MYR 800.00. Bank payments: MYR 300.00 on 8 Jul and MYR 500.00 on 10 Jul.",
         "Same client and invoice reference; both dates eligible. Invoice balance: MYR 0.00."),
        ("11 Jul", "Monthly bank fee", "−8.00", "No supporting document", "none", "file-text",
         "Recorded in your bank cash totals. No invoice or receipt attached.",
         "Missing support alone does not mean this transaction is wrong."),
    ]
    rows = "".join(f"""<tr>
      <td><strong>{party}</strong><div class="reason">{day}</div><span class="badge badge-outline">{icon("bank")}Bank recorded</span></td>
      <td class="r num">{amount}</td>
      <td data-cell="wide"><span class="match-chip {tone}">{icon(symbol)}<span>{label}</span></span>
        <p class="reason">{allocation}</p><p class="reason">{reason}</p></td>
    </tr>""" for day, party, amount, label, tone, symbol, allocation, reason in bank_rows)
    content = f"""
<div class="page stack gap-6">
  <header class="stack gap-2">
    <h1 class="type-title">July reconciliation</h1>
    <p class="muted">Bank cash comes from your statement. Supporting documents explain each payment.</p>
    <p class="muted">Workspace currency: MYR. Synthetic preview.</p>
  </header>
  {seg("recon", [("bank", "Bank evidence"), ("documents", "Documents first"), ("currency", "Currency check")], "bank", "Reconciliation examples", touch=True)}
  <p class="muted" role="status" data-demo-status hidden></p>
  <section class="stack gap-4" data-show-group="recon" data-show-value="bank" aria-labelledby="bank-evidence-h">
    <h2 class="type-h2" id="bank-evidence-h">4 bank transactions, 3 supporting invoices</h2>
    <p>These examples include one payment for two invoices and one invoice paid in two transfers.
      Bank recorded means the transaction appears in the uploaded statement; integrity checks remain separate.</p>
    <div class="table-panel rt-wrap"><table class="data-table rt">
      <thead><tr><th>Bank evidence</th><th class="r">Amount, MYR</th><th>Document support</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
    <details class="disclosure">
      <summary>Explain a transaction without supporting documents {icon("chevron-down")}</summary>
      <div class="stack gap-3">
        <p>Monthly bank fee: MYR 8.00. It already counts in money out.</p>
        <label class="field">Reason<textarea class="input" rows="2">Bank fee charged directly by the bank.</textarea></label>
        <button class="button button-secondary button-lg" type="button" data-demo="Support note saved in this preview">No document needed</button>
      </div>
    </details>
    <p class="muted">A completed extraction is not a reconciled month. Statement coverage, matches and open issues are checked separately.</p>
    <a class="button button-secondary button-lg" href="month.html">See an integrity investigation</a>
  </section>
  <section class="stack gap-4" data-show-group="recon" data-show-value="documents" hidden aria-labelledby="documents-first-h">
    <h2 class="type-h2" id="documents-first-h">Your documents are ready for the statement</h2>
    <p>Add the statement when it arrives, including at month end. Kredibel will check these documents against its transactions.</p>
    <div class="table-panel rt-wrap"><table class="data-table rt">
      <thead><tr><th>Document</th><th class="r">Amount, MYR</th><th>Payment evidence</th></tr></thead>
      <tbody>
        <tr><td><strong>Primepack Packaging</strong><div class="reason">Invoice PP-201, 12 Jul</div></td><td class="r num">450.00</td>
          <td data-cell="wide"><span class="match-chip none">{icon("clock")}<span>Waiting for statement</span></span><p class="reason">Payment has not been confirmed. No bank cash recorded.</p></td></tr>
        <tr><td><strong>Green Valley Farms</strong><div class="reason">Receipt GV-202, 13 Jul</div></td><td class="r num">75.00</td>
          <td data-cell="wide"><span class="match-chip manual">{icon("hand")}<span>Payment confirmed by you</span></span><p class="reason">No bank evidence. Maya confirmed MYR 75.00 cash on 13 Jul: paid at the farm. Excluded from bank totals.</p></td></tr>
        <tr><td><strong>Cendana Supplies</strong><div class="reason">Invoice CS-203, 14 Jul</div></td><td class="r num">120.00</td>
          <td data-cell="wide"><span class="match-chip manual">{icon("hand")}<span>Document approved</span></span><p class="reason">Waiting for statement. Approval does not confirm payment.</p></td></tr>
      </tbody>
    </table></div>
    <div class="stack gap-3">
      <h3 class="type-h3">Invoice PP-201: choose what you can confirm</h3>
      <p>Approving this invoice confirms the document is valid. Confirming payment records how much was paid and when.</p>
      <div class="row"><button type="button" class="button button-secondary button-lg" data-demo="Document approval preview: payment remains unconfirmed">Approve document</button>
        <a class="button button-secondary button-lg" href="documents.html">Upload statement</a></div>
      <details class="disclosure" open>
        <summary>Confirm payment manually {icon("chevron-down")}</summary>
        <form class="stack gap-3" onsubmit="event.preventDefault()">
          <label class="field">Amount paid, MYR<input class="input" type="number" value="450.00" min="0.01" max="450" step="0.01" required/></label>
          <label class="field">Payment date<input class="input" type="date" value="2026-07-15" required/></label>
          <label class="field">Payment method<select class="select"><option>Bank transfer</option><option>Cash</option><option>Card</option></select></label>
          <label class="field">Reason<textarea class="input" rows="2" required>Paid the supplier; waiting for July's statement.</textarea></label>
          <p class="muted">This records your confirmation, with no bank evidence. It does not change bank cash totals. A smaller amount leaves a partial payment.</p>
          <button type="submit" class="button button-primary button-lg" data-demo="Manual payment confirmation preview; no bank cash created">Confirm payment manually</button>
        </form>
      </details>
    </div>
  </section>
  <section class="stack gap-4" data-show-group="recon" data-show-value="currency" hidden aria-labelledby="currency-check-h">
    <h2 class="type-h2" id="currency-check-h">Confirm document currency</h2>
    <p>Your workspace uses MYR, fixed at onboarding. Invoice DEMO-204 says IDR.</p>
    <span class="badge badge-medium">{icon("circle-alert")}Currency needs confirmation</span>
    <p>The document says IDR 1,500.00. Use its amounts as MYR 1,500.00 without conversion?</p>
    <p class="muted">The numbers will stay the same. We keep the printed currency and your confirmation.
      Until you agree, this document stays out of totals and matching.</p>
    <div class="row"><button type="button" class="button button-primary button-lg" data-demo="Currency agreement preview: numeric amounts unchanged">Use amounts as MYR</button>
      <a class="button button-secondary button-lg" href="documents.html">Replace document</a></div>
  </section>
</div>"""
    return shell("months", topbar("Reconciliation", ("Reconciliation",)), content, fab=False, currency="MYR")


# ------------------------------------------------------------------------------------------------
# Month, all months and review: drawn from the same synthetic fixtures as the browser parity checks
# (contracts/design/fixtures/month.json and review.json, AC-019-3) with the app's own words.
# ------------------------------------------------------------------------------------------------

MONTH_WORDS = json.loads((LOCALES / "months.json").read_text(encoding="utf-8"))
DOC_WORDS = json.loads((LOCALES / "documents.json").read_text(encoding="utf-8"))
COMMON_WORDS = json.loads((LOCALES / "common.json").read_text(encoding="utf-8"))
MONTH_FIX = json.loads((ROOT / "contracts/design/fixtures/month.json").read_text(encoding="utf-8"))
MONTH_INVOICES = [i for i in MONTH_FIX["invoices"] if i["month"] == MONTH_FIX["month"]["month"]]
MONTH_RECEIPTS = [r for r in MONTH_FIX["receipts"] if r["month"] == MONTH_FIX["month"]["month"]]
DOC_FIX = json.loads((ROOT / "contracts/design/fixtures/document.json").read_text(encoding="utf-8"))
REVIEW_FIX = json.loads((ROOT / "contracts/design/fixtures/review.json").read_text(encoding="utf-8"))

SUPPORT_CHIP = {"AUTO": ("auto", "link"), "MANUAL": ("manual", "hand"), "PROPOSED": ("proposed", "eye"),
                "NOT_REQUIRED": ("cleared", "check"), "EXCLUDED": ("excluded", "refresh"),
                "NO_SUPPORT": ("none", "file-text"), "NOT_RUN": ("none", "clock")}
CASHFLOW_BADGE = {"OPERATING": "brand", "INVESTING": "low", "FINANCING": "evidence", "NON_CASH": "outline", "UNCLASSIFIED": "medium"}
STATE_BADGE = {"COLLECTING": "outline", "RECONCILING": "low", "NEEDS_REVIEW": "medium", "RECONCILED": "clean", "SIGNED_OFF": "clean"}
DOC_TYPE_BADGE = {"BANK_STATEMENT": "brand", "SALES_INVOICE": "clean", "PURCHASE_INVOICE": "evidence", "RECEIPT": "low", "LEDGER_EXPORT": "outline"}
READING_MARK = {"AGREED": "reading-agreed", "SINGLE_SOURCE": "reading-single", "CONFLICT": "reading-conflict", "MISSING": "reading-conflict"}


def mw(key: str, **params) -> str:
    return words(MONTH_WORDS, key, **params)


def dw(key: str, **params) -> str:
    return words(DOC_WORDS, key, **params)


def fmt_date(iso: str) -> str:
    """The app's formatDate: 9 Feb 2026."""
    year, month, day = iso.split("-")
    return f"{int(day)} {MONTH_NAMES[int(month) - 1][:3]} {year}"


def money_code(value: str, currency: str = "IDR") -> str:
    """The app's formatMoney: the code, a no-break space and the amount (whole units for IDR)."""
    sign = "-" if value.startswith("-") else ""
    return f"{sign}{currency} {amount(value.lstrip('-'))}"


def badge(variant: str, text: str, ic: str | None = None) -> str:
    return f'<span class="badge badge-{variant}">{icon(ic, "icon icon-sm") if ic else ""}{escape(text)}</span>'


def column_attrs(kind: str) -> str:
    """A column's classes as DataTable.tsx builds them: "r" right-aligned, "hide" hidden on phones,
    "wide" full width on phones, any other word a class of its own ("small")."""
    parts = kind.split()
    classes = (["r"] if "r" in parts else []) + (["hide-rt"] if "hide" in parts else []) + [p for p in parts if p not in ("r", "hide", "wide")]
    cell = "hide" if "hide" in parts else "wide" if "wide" in parts else ""
    return (f' class="{" ".join(classes)}"' if classes else "") + (f' data-cell="{cell}"' if cell else "")


def data_table(filters: list[tuple[str, int]], active: int, filter_label: str, search: str, columns: list[tuple[str, str]],
               rows: str, actions: str = "", pager: str = "", footer: str = "", table_class: str = "",
               pages: tuple[int, int] | None = None) -> str:
    """The shared DataTable (docs/12 §7): chips, search, header actions, the responsive table, the pager
    (with Previous, the page and Next when `pages` is (current, total) and there is more than one)."""
    chips = "".join(f'<a class="chip" aria-pressed="{str(i == active).lower()}" href="#">{label} <span class="n">{n}</span></a>'
                    for i, (label, n) in enumerate(filters))
    search_html = (f'<div class="table-search">{icon("search", "icon icon-sm table-search-icon")}'
                   f'<input type="text" class="input input-sm table-search-input" placeholder="{search}" aria-label="{search}"/></div>')
    actions_html = f'<div class="table-actions">{actions}</div>' if actions else ""
    ths = "".join(f'<th{column_attrs(kind)}>{label}</th>' for label, kind in columns)
    return f"""
<div class="stack gap-3">
  <div class="table-toolbar">
    <div class="chips" role="group" aria-label="{filter_label}">{chips}</div>
    <div class="row ml-auto">{search_html}{actions_html}</div>
  </div>
  <div class="table-panel rt-wrap"><table class="{f"data-table rt {table_class}".strip()}"><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table></div>
  {f'<div class="pager-line"><span>{pager}</span>{page_buttons(*pages) if pages and pages[1] > 1 else ""}</div>' if pager else ''}
  {footer}
</div>"""


def page_buttons(current: int, total: int) -> str:
    """DataTable.tsx's page control: Previous, "Page n of m", Next."""
    prev = " disabled" if current <= 1 else ""
    nxt = " disabled" if current >= total else ""
    return (f'<span class="row items-center gap-2"><button type="button" class="button button-secondary button-sm"{prev}>{words(COMMON_WORDS, "table.previous")}</button>'
            f'<span class="muted small">{words(COMMON_WORDS, "table.page", current=current, total=total)}</span>'
            f'<button type="button" class="button button-secondary button-sm"{nxt}>{words(COMMON_WORDS, "table.next")}</button></span>')


def reading_legend(table: dict, prefix: str) -> str:
    sample = words(table, f"{prefix}.sample" if prefix == "legend" else "monthDetail.legendSample")
    keys = (("agreed", "legendAgreed"), ("single", "legendSingle"), ("conflict", "legendConflict"))
    parts = []
    for mark, month_key in keys:
        text = words(table, f"legend.{mark}") if prefix == "legend" else words(table, f"monthDetail.{month_key}")
        parts.append(f'<span><span class="reading reading-{mark}">{sample}</span> {text}</span>')
    return f'<p class="reading-legend">{"".join(parts)}</p>'


# ------------------------------------------------------------------------------------------------
# Month (the reconciliation of March, from month.json)
# ------------------------------------------------------------------------------------------------

def finding_chips(summary: str, findings: list[dict]) -> str:
    """The explainer's [[finding:…]] markers as citation chips with the finding's code (A01); other
    markers are dropped, as the page does."""
    codes = {f["findingId"]: f["code"].split("_")[0] for f in findings}
    out = []
    for part in re.split(r"(\[\[[a-zA-Z0-9_]+:[^\]]+\]\])", summary):
        m = re.match(r"^\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]$", part)
        if not m:
            out.append(escape(part))
        elif m.group(1) == "finding" and m.group(2) in codes:
            out.append(f' <a class="citation" href="evidence-viewer.html">{icon("eye", "icon icon-sm")}{codes[m.group(2)]}</a>')
    return "".join(out).replace(" .", ".").replace("  ", " ")


def month_line_row(line: dict, matches: dict, currency: str) -> str:
    kind = line.get("support") or "NOT_RUN"
    if kind == "MATCHED":
        kind = "MANUAL" if line["match"]["state"] == "MANUAL" else "AUTO"
    chip, ic = SUPPORT_CHIP[kind]
    match = matches.get((line["match"].get("matchIds") or [None])[0])
    if kind in ("AUTO", "MANUAL"):
        reason = ", ".join(mw(f"monthDetail.matchReasons.{r}") for r in (match or {}).get("reasons", []))
    else:
        reason = mw(f"monthDetail.supportReason.{kind}")
    incoming = not line["amount"]["amount"].startswith("-")
    cashflow = line.get("cashflowClass") or "UNCLASSIFIED"
    category = mw(f"categories.{line.get('category') or 'UNKNOWN'}")
    badges = badge(CASHFLOW_BADGE[cashflow], category)
    if cashflow != "UNCLASSIFIED":
        badges += badge("outline", mw("ifrsLabel", classification=mw(f"cashflow.{cashflow}")))
    if line.get("categorizedBy") == "USER":
        badges += f'<span class="reason">{mw("monthDetail.categoryByYou")}</span>'
    name = line.get("counterpartyName") or line["description"].split("\n")[0]
    mark = READING_MARK[line.get("readings", {}).get("amount", {}).get("status", "AGREED")]
    if kind in ("EXCLUDED", "NOT_RUN"):
        action = ""
    elif kind in ("AUTO", "MANUAL") and match:
        action = f'<button class="button button-secondary button-sm" type="button">{mw("monthDetail.unmatch")}</button>'
    else:
        action = f'<button class="button button-secondary button-sm" type="button">{mw("monthDetail.match")}</button>'
    return f"""<tr>
  <td data-cell="wide"><div class="stack gap-1"><strong>{escape(name)}</strong><div class="reason">{fmt_date(line["date"])}</div><div class="row">{badges}</div></div></td>
  <td class="r"><span class="{"amt-in" if incoming else "amt-out"}"><span class="reading {mark}">{"+" if incoming else ""}{amount(line["amount"]["amount"])}</span></span></td>
  <td data-cell="wide"><div><span class="match-chip {chip}">{icon(ic, "icon icon-sm")}<span>{mw(f"monthDetail.support.{kind}")}</span></span>{f'<div class="reason">{reason}</div>' if reason else ''}</div></td>
  <td class="r">{action}</td>
</tr>"""


def month() -> str:
    data = MONTH_FIX["month"]
    lines = MONTH_FIX["lines"]
    matches = {m["matchId"]: m for m in MONTH_FIX["matches"]}
    figures = {k: v["value"] for k, v in data["figures"].items()}
    currency = "IDR"
    label = month_name(data["month"])
    credits = sum(1 for l in lines if not l["amount"]["amount"].startswith("-"))
    # Money in and out leave out transfers between own accounts (NON_CASH), as the app does.
    counted = [l for l in lines if l.get("cashflowClass") != "NON_CASH"]
    counted_credits = sum(1 for l in counted if not l["amount"]["amount"].startswith("-"))
    own_in = credits - counted_credits
    own_out = len(lines) - len(counted) - own_in

    def own(n: int) -> str:
        return f' · {mw("monthDetail.ownAccountsNotCounted", count=n)}' if n else ""
    in_scope = int(figures["bankLines"]) - int(figures["excluded"])
    auto, manual, open_ = int(figures["autoMatched"]), int(figures["manuallyMatched"]), int(figures["proposed"]) + int(figures["unmatched"])
    total = auto + manual + open_
    rate = round(float(figures["autoMatchRate"]) * 100)
    risk = data["risk"]
    documents = len(MONTH_INVOICES) + len(MONTH_RECEIPTS)
    findings = [f for f in MONTH_FIX["findings"] if f["status"] in ("OPEN", "ACKNOWLEDGED")]

    figs = f"""
<section class="ledger" aria-label="{mw("monthDetail.figuresAria", month=label)}">
  <dl class="ledger-figures">
    <div><dt>{mw("monthDetail.openingBalance")}</dt><dd class="v"><small>{currency}</small>{amount(figures["opening"])}</dd><dd class="n">{mw("monthDetail.fromPreviousClosing")}</dd></div>
    <div><dt>{mw("monthDetail.moneyIn")}</dt><dd class="v"><small>{currency}</small>{amount(figures["moneyIn"])}</dd><dd class="n">{mw("monthDetail.creditsRecorded", count=counted_credits)}{own(own_in)}</dd></div>
    <div><dt>{mw("monthDetail.moneyOut")}</dt><dd class="v"><small>{currency}</small>{amount(figures["moneyOut"].lstrip("-"))}</dd><dd class="n">{mw("monthDetail.debitsRecorded", count=len(counted) - counted_credits)}{own(own_out)}</dd></div>
    <div><dt>{mw("monthDetail.closingBalance")}</dt><dd class="v"><small>{currency}</small>{amount(figures["closing"])}</dd><dd class="n">{mw("monthDetail.asPrintedOnStatement")}</dd></div>
    <div><dt>{mw("monthDetail.matchedByKredibel")}</dt><dd class="v">{rate}%</dd><dd class="n">{mw("monthDetail.allocatedToDocs", matched=auto, total=in_scope)}</dd><dd class="mini"><i style="width:{rate}%"></i></dd></div>
    <div><dt>{mw("monthDetail.ledgerDifference")}</dt><dd class="v"><small>{currency}</small>{amount(figures["ledgerDifference"])}</dd><dd class="n">{mw("monthDetail.differenceWithLedger")}</dd></div>
  </dl>
</section>"""
    steps = "".join(f"<li>{escape(s)}</li>" for s in risk["nextSteps"])
    explain = f"""
<section class="explain" aria-labelledby="ex-h">
  <h2 class="explain-head" id="ex-h">{icon("shield-alert")}{mw(f"monthDetail.explainHead.{risk['level']}")}</h2>
  <div class="explain-body">
    <p class="lead">{finding_chips(risk["summary"], MONTH_FIX["findings"])}</p>
    <div class="stack gap-2"><h3 class="type-h3">{mw("monthDetail.whatNext")}</h3><ol class="steps">{steps}</ol></div>
    <span class="by-line">{icon("sparkles", "icon icon-sm")}{mw("monthDetail.byline")}</span>
  </div>
</section>"""
    meter = f"""
<section class="recon-meter" aria-label="{mw("monthDetail.meterAria")}">
  <div class="bar"><i class="auto" style="width:{auto / total * 100:.1f}%"></i><i class="manual" style="width:{manual / total * 100:.1f}%"></i><i class="open" style="width:{open_ / total * 100:.1f}%"></i></div>
  <p class="key"><span><i class="auto"></i>{mw("monthDetail.matchedByKredibel")} <b>{auto}</b></span><span><i class="manual"></i>{mw("monthDetail.matchedByYou")} <b>{manual}</b></span><span><i class="open"></i>{mw("monthDetail.open")} <b>{open_}</b></span></p>
</section>"""
    tab_counts = {"lines": len(lines), "documents": documents, "ledger": None, "findings": len(findings)}
    tabs = "".join(
        f'<a class="tab" role="tab" aria-selected="{str(key == "lines").lower()}" href="#">{mw(f"monthDetail.tabs.{key}")}'
        + (f' <span class="count{" is-attn" if key == "findings" and n else ""}">{n}</span>' if n is not None else "") + "</a>"
        for key, n in tab_counts.items())
    is_open = lambda l: (l.get("support") in ("PROPOSED", "NO_SUPPORT")) or not l.get("support")  # noqa: E731
    rows = "".join(month_line_row(l, matches, currency) for l in lines)
    table = data_table(
        filters=[(mw("monthDetail.filterAll"), len(lines)), (mw("monthDetail.filterOpen"), sum(1 for l in lines if is_open(l))),
                 (mw("monthDetail.filterIn"), credits), (mw("monthDetail.filterOut"), len(lines) - credits)],
        active=0, filter_label=mw("monthDetail.filterBankLines"), search=mw("monthDetail.searchPlaceholder"),
        columns=[(mw("monthDetail.colBankLine"), "wide"), (mw("monthDetail.colAmount", currency=currency), "r"), (mw("monthDetail.colMatchedWith"), "wide"), (mw("monthDetail.colActions"), "r")],
        rows=rows, actions=f'<button class="button button-secondary button-sm" type="button">{mw("monthDetail.reReconcile")}</button>',
        pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(lines), "total": len(lines)}),
        footer=reading_legend(MONTH_WORDS, "monthDetail"))
    content = f"""
<div class="page">
  <div class="month-head">
    <div class="row">
      <span class="month-switch"><a href="month.html" aria-label="{mw("monthDetail.previousMonth")}">{icon("chevron-left")}</a><a href="month.html" aria-label="{mw("monthDetail.nextMonth")}">{icon("chevron-right")}</a></span>
      <h1 class="type-title">{label}</h1>
      <a class="link small" href="months.html">{mw("monthDetail.allMonths")}</a>
      {badge(STATE_BADGE[data["state"]], mw(f"monthDetail.states.{data['state']}"))}
      {badge("critical", mw("monthDetail.critical"), "shield-alert") if risk["level"] == "CRITICAL" else ""}
      <a class="button button-quiet button-sm ml-auto" href="assistant.html">{icon("sparkles", "icon icon-sm")}{mw("monthDetail.askAboutMonth")}</a>
    </div>
    <p class="muted">{escape(data.get("note") or mw("monthDetail.subtitle"))}</p>
  </div>
  <div class="stack gap-6 mt-6">
    {figs}
    {explain}
    {meter}
    <nav class="tabs" role="tablist" aria-label="{mw("monthDetail.sectionsAria", month=label)}">{tabs}</nav>
    <div role="tabpanel">{table}</div>
  </div>
</div>"""
    return shell("months", topbar(label, ((mw("title"), "months.html"), label), back=("Dashboard", "dashboard.html")), content)


PAYMENT_CHIP = {"PAID_BANK": ("auto", "link"), "PARTIAL_BANK": ("proposed", "link"), "PROPOSED": ("proposed", "eye"),
                "CONFIRMED_BY_YOU": ("manual", "hand"), "PAID_CASH": ("cleared", "wallet"), "WAITING_FOR_STATEMENT": ("none", "clock"),
                "NO_BANK_MATCH": ("none", "unlink"), "NOT_DUE": ("excluded", "calendar"), "UNPAID": ("overdue", "circle-alert"),
                "CURRENCY_TO_CONFIRM": ("proposed", "globe"), "NOT_RUN": ("none", "clock")}
PAID = ("PAID_BANK", "CONFIRMED_BY_YOU", "PAID_CASH")
REASONED = ("PROPOSED", "NOT_REQUIRED", "EXCLUDED", "NO_SUPPORT", "NOT_RUN")


def amount_in(value: str, currency: str) -> str:
    """The app's formatAmount: whole units for IDR, two decimals otherwise, no code."""
    return amount(value) if currency == "IDR" else f"{Decimal(value):,.2f}"


def record_rows(records: list[dict] | None = None) -> list[dict]:
    """Invoices and receipts as the app's rows (useMonthDocuments), oldest first."""
    rows = []
    for i in MONTH_FIX["invoices"]:
        ev = i.get("evidence") or {}
        rows.append({"id": i["invoiceId"], "docId": i["docId"], "kind": i["kind"], "number": i.get("number"), "month": i.get("month"),
                     "party": i.get("buyerName") if i["kind"] == "SALES" else i.get("issuerName"), "date": i.get("issueDate"),
                     "total": i.get("total"), "payment": ev.get("payment") or "NOT_RUN", "printedCurrency": ev.get("printedCurrency"),
                     "noCurrencyPrinted": bool(ev) and not ev.get("printedCurrency"), "approved": bool(ev.get("approved"))})
    for r in MONTH_FIX["receipts"]:
        ev = r.get("evidence") or {}
        rows.append({"id": r["receiptId"], "docId": r["docId"], "kind": "RECEIPT", "number": r.get("number"), "month": r.get("month"),
                     "party": r.get("merchantName"), "date": r.get("date"), "total": r.get("total"), "payment": ev.get("payment") or "NOT_RUN",
                     "printedCurrency": ev.get("printedCurrency"), "noCurrencyPrinted": bool(ev) and not ev.get("printedCurrency"),
                     "approved": bool(ev.get("approved"))})
    return sorted(rows, key=lambda r: (r["date"] or "", r["id"]))


def row_title(r: dict) -> str:
    if r["kind"] == "RECEIPT":
        return mw("monthDetail.docs.receipt", number=r["number"]) if r.get("number") else mw("monthDetail.docs.receiptNoNumber")
    return mw("monthDetail.docs.invoice", number=r["number"]) if r.get("number") else mw("monthDetail.docs.invoiceNoNumber")


def row_who(r: dict) -> str:
    party = r.get("party") or mw("monthDetail.docs.unknownParty")
    key = {"SALES": "sales", "PURCHASE": "purchase"}.get(r["kind"], "merchant")
    return mw(f"monthDetail.docs.{key}", party=party)


def months_bank_view(currency: str) -> str:
    """Bank evidence: every line with what supports it, newest first (BankEvidenceView)."""
    # newest first, ties by id ascending (the app's sort)
    lines = sorted(sorted(MONTH_FIX["lines"], key=lambda l: l["txId"]), key=lambda l: l.get("date") or "", reverse=True)
    def kind_of(l: dict) -> str:
        k = l.get("support") or "NOT_RUN"
        return ("MANUAL" if l["match"].get("state") == "MANUAL" else "AUTO") if k == "MATCHED" else k
    rows = []
    for l in lines:
        k = kind_of(l); chip, ic = SUPPORT_CHIP[k]
        v = l["amount"]["amount"]; incoming = not v.startswith("-")
        name = l.get("counterpartyName") or l["description"].split("\n")[0]
        reason = f'<span class="reason">{mw(f"monthDetail.supportReason.{k}")}</span>' if k in REASONED else ""
        action = f'<button class="button button-secondary button-sm" type="button">{mw("monthDetail.match")}</button>' if k in ("NO_SUPPORT", "PROPOSED") else ""
        rows.append(f"""<tr>
  <td data-cell="wide"><div><strong>{escape(name)}</strong><div class="reason">{fmt_date(l["date"])}</div></div></td>
  <td class="hide-rt" data-cell="hide">{month_name(l["month"])}</td>
  <td class="r num"><span class="{"amt-in" if incoming else "amt-out"}">{"+" if incoming else ""}{amount_in(v, currency)}</span></td>
  <td data-cell="wide"><div class="stack gap-1"><span class="match-chip {chip}">{icon(ic, "icon icon-sm")}<span>{mw(f"monthDetail.support.{k}")}</span></span>{reason}</div></td>
  <td class="r">{action}</td>
</tr>""")
    kinds = [("NO_SUPPORT",), ("PROPOSED",), ("AUTO", "MANUAL"), ("NOT_REQUIRED",), ("EXCLUDED",)]
    labels = [mw("monthDetail.support.NO_SUPPORT"), mw("monthDetail.support.PROPOSED"), mw("all.bank.filterMatched"),
              mw("monthDetail.support.NOT_REQUIRED"), mw("monthDetail.support.EXCLUDED")]
    filters = [(mw("monthDetail.filterAll"), len(lines))] + [(label, sum(1 for l in lines if kind_of(l) in ks)) for label, ks in zip(labels, kinds)]
    table = data_table(filters=filters, active=0, filter_label=mw("all.bank.filterLabel"), search=mw("monthDetail.searchPlaceholder"),
                       columns=[(mw("monthDetail.colBankLine"), "wide"), (mw("all.colMonth"), "hide"), (mw("monthDetail.colAmount", currency=currency), "r"),
                                (mw("monthDetail.colMatchedWith"), "wide"), (mw("monthDetail.colActions"), "r")],
                       rows="".join(rows), pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(lines), "total": len(lines)}))
    return f"""<section class="stack gap-4" data-show-group="monthsview" data-show-value="bank" hidden aria-labelledby="bank-evidence-h">
    <h2 class="type-h2" id="bank-evidence-h">{mw("all.bank.title")}</h2>
    <p class="muted">{mw("all.bank.intro")}</p>
    {table}
  </section>"""


def months_docs_view(currency: str) -> str:
    """Documents first: every invoice and receipt by its payment evidence (DocumentsFirstView)."""
    rows = sorted(sorted(record_rows(), key=lambda r: r["id"]), key=lambda r: r["date"] or "", reverse=True)
    trs = []
    for r in rows:
        chip, ic = PAYMENT_CHIP[r["payment"]]
        approved = badge("clean", mw("all.docs.approved")) if r["approved"] else ""
        actions = ""
        if not r["approved"]:
            actions += f'<button class="button button-secondary button-sm" type="button">{mw("all.docs.approve")}</button>'
        if r["payment"] not in PAID and r["payment"] != "CURRENCY_TO_CONFIRM":
            actions += f'<button class="button button-secondary button-sm" type="button">{mw("all.docs.confirmPayment")}</button>'
        printed = f'<div class="reason">{mw("monthDetail.docs.noCurrencyPrinted", currency=currency)}</div>' if r["noCurrencyPrinted"] else ""
        total = r["total"]
        trs.append(f"""<tr>
  <td data-cell="wide"><div><strong>{row_title(r)}</strong><div class="reason">{row_who(r)}</div><div class="reason">{fmt_date(r["date"])}</div>{printed}</div></td>
  <td class="r num">{amount_in(total["amount"], total["currency"]) if total else "—"}</td>
  <td data-cell="wide"><div class="stack gap-1"><span class="match-chip {chip}">{icon(ic, "icon icon-sm")}<span>{mw(f"monthDetail.payment.{r['payment']}")}</span></span>{approved}</div></td>
  <td class="r"><div class="row gap-2 justify-end flex-wrap">{actions}</div></td>
</tr>""")
    groups = [(mw("monthDetail.payment.WAITING_FOR_STATEMENT"), ("WAITING_FOR_STATEMENT", "NOT_DUE")),
              (mw("monthDetail.payment.NO_BANK_MATCH"), ("NO_BANK_MATCH", "PROPOSED", "PARTIAL_BANK")),
              (mw("monthDetail.payment.UNPAID"), ("UNPAID",)), (mw("monthDetail.docs.filterPaid"), PAID)]
    filters = [(mw("monthDetail.docs.filterAll"), len(rows))] + [(label, sum(1 for r in rows if r["payment"] in ps)) for label, ps in groups]
    table = data_table(filters=filters, active=0, filter_label=mw("all.docs.filterLabel"), search=mw("monthDetail.docs.search"),
                       columns=[(mw("monthDetail.docs.colDocument"), "wide"), (mw("monthDetail.docs.colAmount", currency=currency), "r"),
                                (mw("monthDetail.docs.colPayment"), "wide"), (mw("monthDetail.colActions"), "r")],
                       rows="".join(trs), pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(rows), "total": len(rows)}))
    return f"""<section class="stack gap-4" data-show-group="monthsview" data-show-value="documents" hidden aria-labelledby="documents-first-h">
    <h2 class="type-h2" id="documents-first-h">{mw("all.docs.title")}</h2>
    <p class="muted">{mw("all.docs.intro")}</p>
    {table}
  </section>"""


def months_currency_view(currency: str) -> str:
    """Currency: documents printed in another currency, waiting for an agreement (CurrencyView)."""
    pending = [r for r in record_rows() if r["payment"] == "CURRENCY_TO_CONFIRM"]
    cards = []
    for r in pending:
        printed = r.get("printedCurrency") or (r["total"] or {}).get("currency") or ""
        shown = amount_in(r["total"]["amount"], printed or currency)
        cards.append(f"""<article class="card stack gap-3" aria-label="{row_title(r)}">
      <span class="badge badge-medium self-start">{icon("circle-alert", "icon icon-sm")}{mw("all.currency.badge")}</span>
      <p><strong>{row_title(r)}</strong><span class="muted"> · {row_who(r)}</span></p>
      <p>{mw("all.currency.question", printed=printed, amount=shown, currency=currency)}</p>
      <p class="muted">{mw("all.currency.keep")}</p>
      <div class="row gap-3 flex-wrap"><button class="button button-primary" type="button">{mw("all.currency.use", currency=currency)}</button>
        <a class="button button-secondary" href="documents.html">{mw("all.currency.replace")}</a></div>
    </article>""")
    body = "".join(cards) if cards else f'<p class="muted">{mw("all.currency.none", currency=currency)}</p>'
    return f"""<section class="stack gap-4" data-show-group="monthsview" data-show-value="currency" hidden aria-labelledby="currency-check-h">
    <h2 class="type-h2" id="currency-check-h">{mw("all.currency.title")}</h2>
    <p class="muted">{mw("all.currency.intro", currency=currency)}</p>
    {body}
  </section>"""


def months() -> str:
    """All months (/months/all): one row per month with its state, risk and statements, and the
    bank evidence, documents-first and currency views on the same synthetic books (T007-10c)."""
    currency = "IDR"
    items = sorted(MONTH_FIX["months"], key=lambda m: m["month"], reverse=True)
    by_state = lambda states: sum(1 for m in items if m["state"] in states)  # noqa: E731
    rows = "".join(f"""<tr class="is-clickable">
  <td data-cell="wide"><div><strong>{month_name(m["month"])}</strong>{f'<div class="reason">{escape(m["note"])}</div>' if m.get("note") else ''}</div></td>
  <td>{badge(STATE_BADGE[m["state"]], mw(f"monthDetail.states.{m['state']}"))}</td>
  <td>{sev_badge(m["risk"]["level"]) if m.get("risk") else f'<span class="muted small">{mw("all.noRisk")}</span>'}</td>
  <td class="hide-rt" data-cell="hide">{mw("all.statementsCount", count=len(m.get("statements", [])))}</td>
</tr>""" for m in items)
    table = data_table(
        filters=[(mw("all.filterAll"), len(items)), (mw("monthDetail.states.NEEDS_REVIEW"), by_state({"NEEDS_REVIEW"})),
                 (mw("monthDetail.states.COLLECTING"), by_state({"COLLECTING", "RECONCILING"})), (mw("monthDetail.states.RECONCILED"), by_state({"RECONCILED", "SIGNED_OFF"}))],
        active=0, filter_label=mw("all.filterLabel"), search=mw("all.search"),
        columns=[(mw("all.colMonth"), "wide"), (mw("all.colStatus"), ""), (mw("all.colRisk"), ""), (mw("all.colStatements"), "hide")],
        rows=rows, pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(items), "total": len(items)}))
    views = seg("monthsview", [(v, mw(f"all.views.{v}")) for v in ("months", "bank", "documents", "currency")], "months", mw("all.viewsLabel"))
    content = f"""
<div class="page stack gap-6">
  <header class="stack gap-2">
    <h1 class="type-title">{mw("title")}</h1>
    <p class="muted">{mw("subtitle")}</p>
    <p class="muted">{mw("workspaceCurrency", currency=currency)}</p>
  </header>
  {views}
  <section class="stack gap-4" data-show-group="monthsview" data-show-value="months" aria-labelledby="all-months-h">
    <h2 class="type-h2" id="all-months-h">{mw("all.title")}</h2>
    {table}
  </section>
  {months_bank_view(currency)}
  {months_docs_view(currency)}
  {months_currency_view(currency)}
</div>"""
    return shell("months", topbar(mw("title"), (mw("title"),)), content)


# ------------------------------------------------------------------------------------------------
# Review queue (from review.json): the queue, the proposal drawer and a value correction
# ------------------------------------------------------------------------------------------------

KIND_ORDER = ["POSSIBLE_DUPLICATE", "PROPOSED_MATCH", "LEDGER_DIFFERENCE", "UNMATCHED_DOCUMENT", "UNMATCHED_BANK_LINE",
              "LOW_CONFIDENCE_VALUE", "CONFIRM_TYPE", "CONFIRM_LEDGER_MAPPING"]


def rw(key: str, **params) -> str:
    return words(REVIEW_WORDS, key, **params)


def review_queue(selected: str | None = None) -> str:
    items = REVIEW_FIX["items"]
    counts = {k: sum(1 for i in items if i["kind"] == k) for k in KIND_ORDER}
    rows = "".join(f"""<tr class="is-clickable{" is-selected" if i["itemId"] == selected else ""}">
  <td data-cell="wide"><div class="qitem"><span class="kind {KIND_TILE.get(i["kind"], "doc")}">{icon(KIND_ICON.get(i["kind"], "inbox"), "icon icon-sm")}</span><span class="t">{escape(i["title"])}</span><span class="s">{rw(f"kinds.{i['kind']}")}</span></div></td>
  <td class="hide-rt" data-cell="hide">{month_name(i["month"], "long") if i.get("month") else rw("noMonth")}</td>
</tr>""" for i in items)
    table = data_table(
        filters=[(rw("all"), len(items))] + [(rw(f"kinds.{k}"), n) for k, n in counts.items() if n],
        active=0, filter_label=rw("filterLabel"), search=rw("search"),
        columns=[(rw("colItem"), "wide"), (rw("colMonth"), "hide")], rows=rows,
        pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(items), "total": len(items)}))
    return f"""
<div class="page review stack gap-6">
  <header class="stack gap-2">
    <h1 class="type-title">{rw("title")}</h1>
    <p class="muted">{rw("subtitle")}</p>
  </header>
  <section class="stack gap-3" aria-label="{rw("open", count=len(items))}">{table}</section>
</div>"""


def review() -> str:
    return shell("review", topbar(rw("title"), (rw("title"),)), review_queue(), fab=False)


def line_subject(line: dict) -> str:
    incoming = not line["amount"]["amount"].startswith("-")
    category = badge(CASHFLOW_BADGE[line.get("cashflowClass") or "UNCLASSIFIED"], mw(f"categories.{line['category']}")) if line.get("category") else ""
    return f"""<div class="subject"><span class="ico">{icon("bank")}</span><span class="t">{escape(line["description"])}</span><span class="amt{" amt-in" if incoming else ""}">{"+" if incoming else ""}{amount(line["amount"]["amount"])}</span>
  <div class="s row"><span>{fmt_date(line["date"])}</span>{category}<a class="citation" href="document.html" title="{rw("panel.seePage")}">{icon("eye", "icon icon-sm")}<span>{rw("panel.seePage")}</span></a><a class="citation" href="document.html" title="{rw("panel.openDocument")}">{icon("external", "icon icon-sm")}</a></div></div>"""


def record_subject(record: dict) -> str:
    is_receipt = "receiptId" in record
    if is_receipt:
        name = mw("monthDetail.docs.receipt", number=record["number"]) if record.get("number") else mw("monthDetail.docs.receiptNoNumber")
        party, day, kind_badge = record.get("merchantName"), record.get("date"), badge("low", mw("monthDetail.docs.badgeReceipt"))
    else:
        name = mw("monthDetail.docs.invoice", number=record["number"]) if record.get("number") else mw("monthDetail.docs.invoiceNoNumber")
        sales = record["kind"] == "SALES"
        party, day = (record.get("buyerName") if sales else record.get("issuerName")), record.get("issueDate")
        kind_badge = badge("clean" if sales else "evidence", mw("monthDetail.docs.badgeSales" if sales else "monthDetail.docs.badgePurchase"))
    meta = ", ".join(x for x in (party, fmt_date(day) if day else None) if x)
    return f"""<div class="subject"><span class="ico">{icon("receipt" if is_receipt else "file-text")}</span><span class="t">{escape(name)}</span><span class="amt">{amount(record["total"]["amount"])}</span>
  <div class="s row"><span>{escape(meta)}</span>{kind_badge}<a class="citation" href="document.html" title="{rw("panel.seePage")}">{icon("eye", "icon icon-sm")}<span>{rw("panel.seePage")}</span></a><a class="citation" href="document.html" title="{rw("panel.openDocument")}">{icon("external", "icon icon-sm")}</a></div></div>"""


def review_drawer(item: dict, body: str, primary: str | None, quiet: list[str], position: int, preview: str = "",
                  primary_disabled: bool = False) -> str:
    items = REVIEW_FIX["items"]
    head = f"""
<div class="fix-head">
  <div class="pager-line">
    <span class="row">{badge("brand", rw(f"kinds.{item['kind']}"), KIND_ICON.get(item["kind"], "inbox"))}{f'<span>{month_name(item["month"], "long")}</span>' if item.get("month") else ''}</span>
    <span class="row"><span>{rw("panel.position", index=position, total=len(items))}</span><a class="icon-button" href="review.html" aria-label="{rw("panel.close")}">{icon("x")}</a></span>
  </div>
  <h2 id="fix-h">{escape(item["title"])}</h2>
  <p>{rw(f"why.{item['kind']}")}</p>
</div>"""
    others = "".join(f'<a class="button button-quiet button-sm" href="#">{label}</a>' for label in quiet)
    foot = f"""
<div class="fix-foot">
  {(f'<button class="button button-primary" type="button" disabled>{icon("check", "icon icon-sm")}<span>{primary}</span></button>' if primary_disabled else f'<a class="button button-primary" href="review.html">{icon("check", "icon icon-sm")}<span>{primary}</span></a>') if primary else ''}
  <a class="button button-secondary" href="review.html">{rw("panel.skip")}</a>
  <span class="keys hide-compact"><span><span class="kbd">J</span> <span class="kbd">K</span> {rw("panel.keys")}</span><span><span class="kbd">{rw("panel.enterKey")}</span> {rw("panel.keyEnter")}</span></span>
</div>"""
    return f"""
<div class="flow-sheet review-sheet">
  <a class="scrim" href="review.html" aria-label="{rw("panel.close")}"></a>
  <section class="sheet review-drawer{" has-preview" if preview else ""}" role="dialog" aria-modal="true" aria-labelledby="fix-h">
    <div class="review-split-layout{" with-preview" if preview else ""}">
      {preview}
      <section class="fix review-split-panel" aria-labelledby="fix-h">
        {head}
        <div class="fix-body">{body}{f'<div class="other-actions">{others}</div>' if others else ''}</div>
        {foot}
      </section>
    </div>
  </section>
</div>"""


def review_match() -> str:
    """The proposal drawer: one bank line, the invoice it fits, why, and Confirm the match."""
    item = REVIEW_FIX["items"][0]
    line = next(l for l in REVIEW_FIX["lines"] if l["txId"] == item["subject"]["bankLineIds"][0])
    invoice = next(i for i in REVIEW_FIX["invoices"] if i["invoiceId"] == item["subject"]["invoiceIds"][0])
    candidate = item["suggestion"]["candidates"][0]
    score = float(candidate["score"])
    tags = "".join(f'<span class="why-tag yes">{icon("check", "icon icon-sm")}{mw(f"monthDetail.matchReasons.{r}")}</span>' for r in candidate["reasons"])
    ranked = sorted((c for c in item["suggestion"]["candidates"] if c.get("aiRank") and c.get("aiReason")), key=lambda c: c["aiRank"])
    ai_items = "".join(
        f'<li><strong>{rw("panel.aiThisProposal") if c["matchId"] == candidate["matchId"] else rw("panel.aiOther")}</strong> {c["aiReason"]}</li>'
        for c in ranked
    )
    ai_view = (f'<section class="ai-view" aria-label="{rw("panel.aiView")}"><p class="ai-view-head">{icon("sparkles", "icon icon-sm")}{rw("panel.aiView")}</p>'
               f'<ol>{ai_items}</ol><p class="muted small">{rw("panel.aiNote")}</p></section>') if ranked else ""
    proposal = f"""
<div class="candidates" role="radiogroup" aria-label="{rw("panel.proposal")}">
  <div class="candidate is-picked" role="radio" aria-checked="true" tabindex="0"><span class="radio"></span><span><span class="t">{rw("panel.proposal")}</span></span>
    <span class="why">{tags}</span>
    <span class="score">{rw("panel.fit")}<span class="meter-bar"><i style="width:{round(score * 100)}%"></i></span><span>{score:.2f}</span></span></div>
  {ai_view}
</div>"""
    body = line_subject(line) + record_subject(invoice) + proposal
    drawer = review_drawer(item, body, rw("actions.CONFIRM_MATCH"), [rw("actions.REJECT_MATCH")], 1)
    return shell("review", topbar(rw("title"), (rw("title"),)), review_queue(item["itemId"]) + drawer, fab=False)


def receipt_page() -> str:
    """A synthetic till receipt (docs/18) for the preview beside a value to check."""
    return f"""
<figure class="doc-page doc-receipt" aria-label="Receipt 0617 from Cendana Fuel Station, 17 Jun 2026, with the total highlighted">
  <div class="watermark" aria-hidden="true">SYNTHETIC — FOR TESTING</div>
  <p class="doc-bank" style="text-align:center"><i aria-hidden="true"></i>CENDANA FUEL STATION</p>
  <p style="text-align:center;margin-top:4px">Jl. Raya Lembang 48, Bandung<br/>17 Jun 2026 14:32 · No. 0617</p>
  <table class="doc-table" style="margin-top:14px">
    <thead><tr><th>Item</th><th class="r">Qty</th><th class="r">Amount</th></tr></thead>
    <tbody>
      <tr><td>Pertamax 92</td><td class="r">41.2 L</td><td class="r">618,000.00</td></tr>
      <tr><td>Engine oil 1 L</td><td class="r">2</td><td class="r">202,000.00</td></tr>
      <tr><td><strong>TOTAL</strong></td><td></td><td class="r"><span class="lamp">820,000.00<span class="lamp-marker" aria-hidden="true">1</span></span></td></tr>
      <tr><td>CASH</td><td></td><td class="r">850,000.00</td></tr>
      <tr><td>CHANGE</td><td></td><td class="r">30,000.00</td></tr>
    </tbody>
  </table>
  <div class="doc-foot"><span>Terima kasih</span><span>SYNTHETIC — FOR TESTING</span></div>
</figure>"""


def doc_preview(doc: dict, page_html: str) -> str:
    """The page beside the panel: the file, its viewer and the synthetic page."""
    return f"""
<aside class="review-split-preview" aria-label="{rw("panel.documentPreview")}">
  <div class="review-preview-header">
    <span class="file">{icon("file-text", "icon icon-sm")}<span>{escape(doc["fileName"])}</span></span>
    <div class="row"><a class="link small" href="document.html" title="{rw("panel.openDocument")}"><span>{rw("panel.openDocument")}</span>{icon("external", "icon icon-sm")}</a><a class="icon-button icon-button-sm" href="review.html" aria-label="Close preview">{icon("x", "icon icon-sm")}</a></div>
  </div>
  <div class="stack">
    <section class="viewer" aria-label="{dw("detail.viewer.label")}">
      <div class="viewer-bar">
        <span class="file">{icon("file-text", "icon icon-sm")}{escape(doc["fileName"])}</span>
        {badge("outline", dw("detail.scanned"))}
        <span class="pages" role="group" aria-label="{dw("detail.viewer.pages")}"><button type="button" aria-label="{dw("detail.viewer.previous")}" disabled>{icon("chevron-left", "icon icon-sm")}</button><span>{dw("detail.viewer.pageOf", page=1, total=1)}</span><button type="button" aria-label="{dw("detail.viewer.next")}" disabled>{icon("chevron-right", "icon icon-sm")}</button></span>
        <span class="zoom" role="group" aria-label="{dw("detail.viewer.zoom")}"><button type="button" aria-label="{dw("detail.viewer.zoomOut")}">{icon("zoom-out", "icon icon-sm")}</button><span>{dw("detail.viewer.zoomLevel", zoom=100)}</span><button type="button" aria-label="{dw("detail.viewer.zoomIn")}">{icon("zoom-in", "icon icon-sm")}</button></span>
      </div>
      <div class="doc-window is-image" tabindex="0">{page_html}</div>
      <p class="muted small">{dw("detail.viewer.hint")}</p>
    </section>
  </div>
</aside>"""


def review_correction() -> str:
    """A value to check: the receipt beside the panel, with the correction form open (T009-03a)."""
    item = next(i for i in REVIEW_FIX["items"] if i["kind"] == "LOW_CONFIDENCE_VALUE")
    receipt = next(r for r in REVIEW_FIX["receipts"] if r["receiptId"] == item["subject"]["receiptIds"][0])
    doc = REVIEW_FIX["documents"][item["subject"]["docIds"][0]]
    position = REVIEW_FIX["items"].index(item) + 1
    preview = doc_preview(doc, receipt_page())
    field = item["subject"]["field"]
    form = f"""
<form class="field" action="review.html" method="get">
  <label class="label" for="correct-value">{rw("panel.correctLabel", field=rw(f"fields.{field}"))}</label>
  <input id="correct-value" class="input" value=""/>
  <p class="muted small">{rw("panel.correctHint")}</p>
  <div class="row"><button class="button button-primary button-sm" type="submit" disabled>{rw("actions.saveCorrection")}</button></div>
</form>"""
    body = record_subject(receipt) + form
    drawer = review_drawer(item, body, rw("actions.ACCEPT_AS_READ"), [], position, preview)
    return shell("review", topbar(rw("title"), (rw("title"),)), review_queue(item["itemId"]) + drawer, fab=False)

def document_subject(doc: dict, label: str, href: str) -> str:
    return f"""<div class="subject"><span class="ico">{icon("files")}</span><span class="t">{escape(doc["fileName"])}</span>
  <div class="s row"><span>{label}</span><a class="citation" href="{href}" title="{rw("panel.openDocument")}">{icon("eye", "icon icon-sm")}<span>{rw("panel.openDocument")}</span></a><a class="citation" href="{href}" title="{rw("panel.openDocument")}">{icon("external", "icon icon-sm")}</a></div></div>"""


MAPPING_FIELDS = ["date", "description", "accountCode", "accountName", "reference"]
DATE_FORMATS = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD", "DD-MM-YYYY", "DD.MM.YYYY"]


def mapping_editor_markup(view: dict) -> str:
    """The MappingEditor: the fields with the file's columns, the amounts' layout, the date format
    and the decimal separator, and the first rows as the mapping reads them (spec 005)."""
    mapping, header = view["mapping"], view["header"]
    first = view["sampleRows"][0]["raw"] if view["sampleRows"] else []
    amount_fields = ["amount"] if mapping.get("amount") else ["debit", "credit"]
    required = {"date", "description", "accountCode", *amount_fields}

    def select(field: str) -> str:
        chosen = mapping.get(field) or ""
        options = f'<option value=""{" selected" if not chosen else ""}>{rw("mapping.notInFile")}</option>' + "".join(
            f'<option value="{escape(h)}"{" selected" if h == chosen else ""}>{escape(h)}</option>' for h in header)
        return f'<select class="input" aria-label="{rw(f"mapping.fields.{field}")}">{options}</select>'

    rows = "".join(
        f'<tr><th scope="row">{rw(f"mapping.fields.{f}")}{" *" if f in required else ""}</th><td>{select(f)}</td>'
        f'<td class="muted small hide-rt">{escape(first[header.index(mapping[f])]) if mapping.get(f) in header else ""}</td></tr>'
        for f in MAPPING_FIELDS + amount_fields)
    mapped = {mapping.get(f) for f in MAPPING_FIELDS + amount_fields if mapping.get(f)}
    sample_head = "".join(f'<th scope="col"{" class=\"is-mapped\"" if h in mapped else ""}>{escape(h)}</th>' for h in header)
    sample_rows = []
    for row in view["sampleRows"]:
        cells = "".join(f'<td class="{"is-mapped" if header[i] in mapped else "muted"}">{escape(c)}</td>' for i, c in enumerate(row["raw"]))
        parsed = row.get("parsed")
        if parsed:
            debit, credit = Decimal(parsed["debit"]["amount"]), Decimal(parsed["credit"]["amount"])
            read = (f'{fmt_date(parsed["date"])} · {parsed["accountCode"]} · '
                    + (f'{rw("mapping.fields.debit")} {amount(parsed["debit"]["amount"])}' if debit else "")
                    + (f'{rw("mapping.fields.credit")} {amount(parsed["credit"]["amount"])}' if credit else ""))
        else:
            read = f'<span class="sev-high">{rw("mapping.sampleUnread", reason=row.get("error") or "")}</span>'
        sample_rows.append(f'<tr>{cells}<td class="small">{read}</td></tr>')
    date_options = "".join(f'<option{" selected" if f == mapping["dateFormat"] else ""}>{f}</option>' for f in DATE_FORMATS)
    amount_layout = "amount" if mapping.get("amount") else "debitCredit"
    sign = (f'<label class="field m-0"><span class="label">{rw("mapping.signConvention")}</span><select class="input">'
            f'<option value="DEBIT_POSITIVE"{" selected" if mapping.get("signConvention") != "CREDIT_POSITIVE" else ""}>{rw("mapping.DEBIT_POSITIVE")}</option>'
            f'<option value="CREDIT_POSITIVE"{" selected" if mapping.get("signConvention") == "CREDIT_POSITIVE" else ""}>{rw("mapping.CREDIT_POSITIVE")}</option></select></label>'
            if amount_layout == "amount" else "")
    return f"""
<div class="mapping stack gap-4">
  <p class="muted small">{rw("mapping.intro")}</p>
  <div class="table-panel"><table class="data-table mapping-fields"><thead><tr><th scope="col">{rw("mapping.field")}</th><th scope="col">{rw("mapping.column")}</th><th scope="col" class="hide-rt">{rw("mapping.sampleRaw")}</th></tr></thead><tbody>{rows}</tbody></table></div>
  <div class="row">
    <fieldset class="field m-0"><legend class="label">{rw("mapping.layout")}</legend><div class="row">
      <label class="row"><input type="radio" name="mapping-layout"{" checked" if amount_layout == "debitCredit" else ""}/>{rw("mapping.layoutDebitCredit")}</label>
      <label class="row"><input type="radio" name="mapping-layout"{" checked" if amount_layout == "amount" else ""}/>{rw("mapping.layoutAmount")}</label>
    </div></fieldset>
    {sign}
    <label class="field m-0"><span class="label">{rw("mapping.dateFormat")}</span><select class="input">{date_options}</select></label>
    <label class="field m-0"><span class="label">{rw("mapping.decimalSeparator")}</span><select class="input"><option value="."{" selected" if mapping["decimalSeparator"] == "." else ""}>{rw("mapping.separatorDot")}</option><option value=","{" selected" if mapping["decimalSeparator"] == "," else ""}>{rw("mapping.separatorComma")}</option></select></label>
  </div>
  <section class="stack gap-2" aria-label="{rw("mapping.sample")}">
    <h3 class="type-h3">{rw("mapping.sample")}</h3>
    <div class="table-panel rt-wrap"><table class="data-table mapping-sample"><thead><tr>{sample_head}<th scope="col">{rw("mapping.sampleRead")}</th></tr></thead><tbody>{"".join(sample_rows)}</tbody></table></div>
  </section>
</div>"""


DOC_TYPES = ["BANK_STATEMENT", "SALES_INVOICE", "PURCHASE_INVOICE", "RECEIPT", "LEDGER_EXPORT", "OTHER"]


def review_type() -> str:
    """A document whose kind the classifier is not sure of: choose it, the page beside (AC-005-2)."""
    item = next(i for i in REVIEW_FIX["items"] if i["kind"] == "CONFIRM_TYPE")
    doc = REVIEW_FIX["documents"][item["subject"]["docIds"][0]]
    position = REVIEW_FIX["items"].index(item) + 1
    guess = item["suggestion"]["docType"]
    confidence = f'{round(float(item["suggestion"]["confidence"]) * 100)}%'
    options = "".join(f'<option value="{t}"{" selected" if t == guess else ""}>{dw(f"detail.docType.{t}")}</option>' for t in DOC_TYPES)
    form = f"""
<div class="field">
  <label class="label" for="doc-type">{rw("panel.docType")}</label>
  <select id="doc-type" class="input">{options}</select>
  <p class="muted small">{rw("panel.docTypeHint", type=dw(f"detail.docType.{guess}"), confidence=confidence)}</p>
</div>"""
    body = document_subject(doc, rw("panel.document"), "document.html") + form
    drawer = review_drawer(item, body, rw("actions.SET_TYPE"), [], position, doc_preview(doc, receipt_page()))
    return shell("review", topbar(rw("title"), (rw("title"),)), review_queue(item["itemId"]) + drawer, fab=False)


def review_mapping() -> str:
    """A ledger export with a new layout: which column is which, confirmed once (T005-11)."""
    item = next(i for i in REVIEW_FIX["items"] if i["kind"] == "CONFIRM_LEDGER_MAPPING")
    view = REVIEW_FIX["ledgerMapping"]
    doc = REVIEW_FIX["documents"][item["subject"]["docIds"][0]]
    position = REVIEW_FIX["items"].index(item) + 1
    body = (document_subject(doc, rw("panel.document"), "document-ledger-columns.html") + mapping_editor_markup(view)
            + f'<p class="muted small">{rw("mapping.incomplete")}</p>')
    drawer = review_drawer(item, body, rw("mapping.confirm"), [], position, primary_disabled=True)
    return shell("review", topbar(rw("title"), (rw("title"),)), review_queue(item["itemId"]) + drawer, fab=False)


# ------------------------------------------------------------------------------------------------
# Evidence viewer (Risk → finding)
# ------------------------------------------------------------------------------------------------

def statement_page(rows: list | None = None, period: str = "01 Mar 2026 to 31 Mar 2026",
                   page: str = "Page 2 / 3", label: str = "March statement, page 2, with two highlighted values") -> str:
    rows = rows or [
        ("10 Mar", "VAT PAYMENT FEB", "4,860,000.00", "", "38,940,000.00", ""),
        ("11 Mar", "TRANSFER IN DAYBREAK CAFE", "", "6,420,000.00", "45,360,000.00", ""),
        ("12 Mar", "TRANSFER OUT GREEN VALLEY FARMS 0912", "9,850,000.00", "", "35,510,000.00", ""),
        ("12 Mar", "CASH DEPOSIT", "", "2,240,000.00", "37,750,000.00", ""),
        ("13 Mar", "TRANSFER IN SPICE ROUTE RESTAURANT", "", "3,500,000.00", "41,250,000.00", ""),
        ("14 Mar", "TRANSFER IN HARBORVIEW HOTEL GROUP", "", "HIT1", "HIT2", "hit"),
        ("15 Mar", "TRANSFER OUT PRIMEPACK PACKAGING", "3,180,000.00", "", "39,320,000.00", ""),
        ("17 Mar", "INSTANT TRANSFER IN HIGHLAND RESORT &amp; SPA", "", "8,900,000.00", "48,220,000.00", ""),
        ("18 Mar", "DEBIT CARD CENDANA FUEL STATION", "650,000.00", "", "47,570,000.00", ""),
        ("19 Mar", "CASH DEPOSIT", "", "1,860,000.00", "49,430,000.00", ""),
        ("20 Mar", "TRANSFER OUT ANDI PRATAMA", "5,000,000.00", "", "44,430,000.00", ""),
    ]
    trs = []
    for d, desc, debit, credit, bal, hit in rows:
        if credit == "HIT1":
            credit = '<span class="lamp helvetica">7,250,000.00<span class="lamp-marker" aria-hidden="true">1</span></span>'
        if bal == "HIT2":
            bal = '<span class="lamp">42,500,000.00<span class="lamp-marker" aria-hidden="true">2</span></span>'
        if hit == "lit":  # the value selected in the document page: one box, no number
            credit = f'<span class="lamp">{credit}</span>' if credit else credit
            debit = f'<span class="lamp">{debit}</span>' if debit else debit
        trs.append(f'<tr><td>{d}</td><td>{desc}</td><td class="r">{debit}</td><td class="r">{credit}</td><td class="r">{bal}</td></tr>')
    return f"""
<figure class="doc-page" aria-label="{label}">
  <div class="watermark" aria-hidden="true">SYNTHETIC — FOR TESTING</div>
  <div class="doc-head">
    <div><p class="doc-bank"><i aria-hidden="true"></i>ARCHIPELAGO COMMERCE BANK</p><p style="margin-top:6px">SUNRISE COFFEE ROASTERS<br/>12 Roastery Lane, Bandung</p></div>
    <div class="meta"><strong>ACCOUNT STATEMENT</strong><br/>{period}<br/>Currency IDR<br/>{page}</div>
  </div>
  <table class="doc-table">
    <thead><tr><th>Date</th><th>Description</th><th class="r">Debit</th><th class="r">Credit</th><th class="r">Balance</th></tr></thead>
    <tbody>{''.join(trs)}</tbody>
  </table>
  <div class="doc-foot"><span>ACB e-Statement</span><span>SYNTHETIC — FOR TESTING</span></div>
</figure>"""


def evidence_viewer() -> str:
    related = [
        ("high", "M04", "Drawn in Helvetica; every other amount in the column uses DejaVu Sans."),
        ("high", "M03", "A later revision of the file replaced this page's content."),
        ("medium", "M02", "Saved 3 days after the bank created the file."),
    ]
    rel = "".join(f'<li>{sev_badge(s)}<span class="code-tag">{c}</span><span style="flex:1;min-width:0">{t}</span></li>' for s, c, t in related)
    drawer = f"""
<div class="drawer" role="dialog" aria-modal="true" aria-labelledby="ev-title">
  <div class="drawer-head">
    <div class="stack gap-2" style="flex:1;min-width:0">
      <div class="row">
        <span class="muted small">March 2026, finding 1 of 6</span>{sev_badge("critical")}<span class="code-tag">A01</span>
      </div>
      <h1 id="ev-title">The running balance does not add up on 14 Mar</h1>
    </div>
    <a class="icon-button" href="risk.html" aria-label="Close evidence">{icon("x")}</a>
  </div>
  <div class="drawer-body">
    <div class="viewer">
      <div class="viewer-bar">
        <span class="file">{icon("file-text", "icon icon-sm")}ACB_Mar_2026.pdf</span>
        <span>Page 2 of 3</span>
        <span class="zoom" role="group" aria-label="Zoom"><button type="button" aria-label="Zoom out">{icon("zoom-out", "icon icon-sm")}</button><span>100%</span><button type="button" aria-label="Zoom in">{icon("zoom-in", "icon icon-sm")}</button></span>
      </div>
      <div class="doc-window">{statement_page()}</div>
      <div class="spread"><p class="muted small">Boxes come from the word positions in the file itself.</p><button class="button button-secondary button-sm whole-page" type="button">{icon("file-text", "icon icon-sm")}Whole page</button></div>
    </div>
    <div class="finding-pane">
      <p class="lead">The balance printed on 14 Mar is <strong>IDR 6,000,000 lower</strong> than the previous balance plus that day's credit. The credit is set in a different font from the rest of its column and was added in a later revision of the file.</p>
      <section aria-labelledby="calc-h">
        <h2 id="calc-h">How the balance should add up</h2>
        <div class="calc"><table>
          <tr><td class="op"></td><td>Balance on 13 Mar</td><td class="amt"><span class="reading reading-agreed">41,250,000.00</span></td></tr>
          <tr><td class="op">+</td><td>Credit on 14 Mar <span class="lamp-marker inline" role="img" aria-label="box 1">1</span></td><td class="amt"><span class="reading reading-agreed">7,250,000.00</span></td></tr>
          <tr><td class="op">−</td><td>Debit on 14 Mar</td><td class="amt">0.00</td></tr>
          <tr class="total"><td class="op">=</td><td>Expected balance</td><td class="amt">48,500,000.00</td></tr>
          <tr><td class="op"></td><td>Printed balance <span class="lamp-marker inline" role="img" aria-label="box 2">2</span></td><td class="amt"><span class="reading reading-agreed">42,500,000.00</span></td></tr>
          <tr class="diff"><td class="op"></td><td>Difference</td><td class="amt">6,000,000.00</td></tr>
        </table></div>
      </section>
      <section aria-labelledby="two-h">
        <h2 id="two-h">Two readings</h2>
        <table class="readings">
          <thead><tr><th>Value</th><th><span class="src">{icon("ai-reader", "icon icon-sm")}Gemini</span></th><th><span class="src">{icon("text-layer", "icon icon-sm")}Text layer</span></th><th>Result</th></tr></thead>
          <tbody>
            <tr><td>Credit, 14 Mar</td><td class="amt">7,250,000.00</td><td class="amt">7,250,000.00</td><td><span class="badge badge-brand">{icon("check")}Agreed</span></td></tr>
            <tr><td>Balance, 14 Mar</td><td class="amt">42,500,000.00</td><td class="amt">42,500,000.00</td><td><span class="badge badge-brand">{icon("check")}Agreed</span></td></tr>
          </tbody>
        </table>
        <p class="muted" style="font-size:13.5px;margin-top:10px">Both readings see the same printed values, so the break is in the document, not in the reading.</p>
      </section>
      <section aria-labelledby="next-h">
        <h2 id="next-h">What to do next</h2>
        <ol class="steps"><li>Download the March statement again from internet banking and upload it.</li><li>If the bank's copy differs, ask who sent you this file.</li></ol>
      </section>
      <section aria-labelledby="rel-h">
        <h2 id="rel-h">Also found on this row</h2>
        <ul class="related">{rel}</ul>
      </section>
    </div>
  </div>
  <div class="drawer-foot">
    <a class="button button-secondary" href="risk.html">{icon("check")}Acknowledge</a>
    <a class="button button-ghost" href="risk.html">Dismiss, with a reason</a>
    <span class="keys"><span><span class="kbd">J</span> <span class="kbd">K</span> next, previous</span><span><span class="kbd">Esc</span> close</span></span>
  </div>
</div>"""
    return f'<div class="viewport"><div class="drawer-frame"><div class="drawer-behind" aria-hidden="true"></div>{drawer}</div></div>'



# ------------------------------------------------------------------------------------------------
# Document (one read statement, and a ledger export), from document.json
# ------------------------------------------------------------------------------------------------

def page_viewer(file_name: str, page: int, total: int, witness: str, figure: str, lit: bool) -> str:
    """The PageViewer: file, witness, pages and zoom above the page window (docs/11 §6.3)."""
    return f"""
<section class="viewer" aria-label="{dw("detail.viewer.label")}">
  <div class="viewer-bar">
    <span class="file">{icon("file-text", "icon icon-sm")}{escape(file_name)}</span>
    {badge("outline", dw("detail.digital" if witness == "TEXT_LAYER" else "detail.scanned"))}
    <span class="pages" role="group" aria-label="{dw("detail.viewer.pages")}"><button type="button" aria-label="{dw("detail.viewer.previous")}"{" disabled" if page <= 1 else ""}>{icon("chevron-left", "icon icon-sm")}</button><span>{dw("detail.viewer.pageOf", page=page, total=total)}</span><button type="button" aria-label="{dw("detail.viewer.next")}"{" disabled" if page >= total else ""}>{icon("chevron-right", "icon icon-sm")}</button></span>
    <span class="zoom" role="group" aria-label="{dw("detail.viewer.zoom")}"><button type="button" aria-label="{dw("detail.viewer.zoomOut")}">{icon("zoom-out", "icon icon-sm")}</button><span>{dw("detail.viewer.zoomLevel", zoom=100)}</span><button type="button" aria-label="{dw("detail.viewer.zoomIn")}">{icon("zoom-in", "icon icon-sm")}</button></span>
  </div>
  <div class="doc-window is-image" tabindex="0"><div class="page-zoom">{figure}</div></div>
  <p class="muted small">{dw("detail.viewer.lit" if lit else "detail.viewer.hint")}</p>
</section>"""


def document_header(doc: dict, summary: str, badges: str) -> str:
    return f"""
  <header class="stack gap-2">
    <h1 class="type-title">{escape(doc["fileName"])}</h1>
    <p class="muted">{summary}</p>
    <div class="doc-status">
      {badges}
      <span class="spacer"></span>
      <span class="row"><button class="button button-secondary button-sm" type="button">{icon("download", "icon icon-sm")}{dw("detail.downloadOriginal")}</button><button class="button button-ghost button-sm" type="button">{icon("trash", "icon icon-sm")}{dw("detail.deleteDocument")}</button></span>
    </div>
  </header>"""


def doc_tabs(tabs: list[tuple[str, int | None]], active: int = 0, attn: str | None = None) -> str:
    items = "".join(
        f'<a class="tab" role="tab" aria-selected="{str(i == active).lower()}" href="#">{label}'
        + (f'<span class="count{" is-attn" if label == attn and n else ""}">{n}</span>' if n is not None else "") + "</a>"
        for i, (label, n) in enumerate(tabs))
    return f'<div class="tabs" role="tablist" aria-label="{dw("detail.tabs.label")}">{items}</div>'


def document() -> str:
    doc, lines = DOC_FIX["document"], DOC_FIX["lines"]
    meta = doc["statementMeta"]
    currency = meta["currency"]
    selected = "tx_feb_09"
    summary = dw("detail.summary.statement", type=dw("detail.docType.BANK_STATEMENT"), account=f'{meta["bankName"]} {meta["accountMasked"]}',
                 start=fmt_date(meta["periodStart"]), end=fmt_date(meta["periodEnd"]), uploaded=fmt_date(doc["uploadedAt"][:10]))
    badges = (badge(DOC_TYPE_BADGE[doc["docType"]], dw(f"detail.docType.{doc['docType']}"))
              + badge("brand", dw("detail.readBadge", agreed=doc["reading"]["fieldsAgreed"], compared=doc["reading"]["fieldsCompared"]), "check")
              + badge("clean", dw(f"detail.verdictBadge.{doc['integrity']['verdict']}"), "shield-check"))
    credits = [l for l in lines if not l["amount"]["amount"].startswith("-")]
    debits = [l for l in lines if l["amount"]["amount"].startswith("-")]
    total = lambda items: money_code(str(sum(Decimal(l["amount"]["amount"].lstrip("-")) for l in items)), currency)  # noqa: E731
    figures = f"""
  <dl class="ledger-figures">
    <div><dt>{dw("detail.opening")}</dt><dd class="v">{money_code(meta["opening"]["amount"], currency)}</dd><dd class="n">{dw("detail.figures.asPrinted", date=fmt_date(meta["periodStart"]))}</dd></div>
    <div><dt>{dw("detail.closing")}</dt><dd class="v">{money_code(meta["closing"]["amount"], currency)}</dd><dd class="n">{dw("detail.figures.asPrinted", date=fmt_date(meta["periodEnd"]))}</dd></div>
    <div><dt>{dw("detail.figures.moneyIn")}</dt><dd class="v">{total(credits)}</dd><dd class="n">{dw("detail.figures.credits", count=len(credits))}</dd></div>
    <div><dt>{dw("detail.figures.moneyOut")}</dt><dd class="v">{total(debits)}</dd><dd class="n">{dw("detail.figures.debits", count=len(debits))}</dd></div>
  </dl>"""
    to_check = [l for l in lines if l.get("source") == "WITNESS" or l["readings"]["amount"]["status"] != "AGREED"]

    def row(line: dict) -> str:
        status = line["readings"]["amount"]["status"]
        incoming = not line["amount"]["amount"].startswith("-")
        where = dw("detail.lines.where", date=fmt_date(line["date"]), page=line["page"])
        check = dw("detail.witnessRow") if line.get("source") == "WITNESS" else (dw(f"detail.readingStatus.{status}") if status != "AGREED" else "")
        mark = READING_MARK["SINGLE_SOURCE"] if line.get("source") == "WITNESS" else READING_MARK[status]
        sel_cls, sel_attr = (" is-selected", ' aria-selected="true"') if line["txId"] == selected else ("", "")
        return (f'<tr class="is-clickable{sel_cls}"{sel_attr}>'
                f'<td data-cell="wide"><div><strong class="block">{escape(line["description"])}</strong><div class="reason">{f"{where} · {check}" if check else where}</div></div></td>'
                f'<td class="r"><span class="{"amt-in" if incoming else "amt-out"}"><span class="reading {mark}">{"+" if incoming else ""}{money_code(line["amount"]["amount"], currency)}</span></span></td></tr>')

    table = data_table(
        filters=[(dw("detail.lines.all"), len(lines)), (dw("detail.lines.in"), len(credits)), (dw("detail.lines.out"), len(debits)), (dw("detail.lines.check"), len(to_check))],
        active=0, filter_label=dw("detail.lines.filter"), search="Search transactions...",
        columns=[(dw("detail.columns.transaction"), "wide"), (dw("detail.columns.amount"), "r")],
        rows="".join(row(l) for l in lines),
        pager=dw("detail.lines.range", **{"from": 1, "to": len(lines), "total": len(lines)}),
        footer=reading_legend(DOC_WORDS["detail"], "legend"))
    pane = f"""
<section class="doc-pane" aria-label="{dw("detail.pane")}">
  {figures}
  {doc_tabs([(dw("detail.tabs.transactions"), len(lines)), (dw("detail.tabs.findings"), 0), (dw("detail.tabs.details"), None)])}
  <div role="tabpanel" class="stack gap-3">{table}</div>
</section>"""
    page_rows = [
        ("2 Feb", "OPENING BALANCE", "", "", "41,100,000.00", ""),
        ("3 Feb", "TRANSFER OUT GREEN VALLEY FARMS 0912", "12,400,000.00", "", "28,700,000.00", ""),
        ("4 Feb", "CASH DEPOSIT", "", "2,050,000.00", "30,750,000.00", ""),
        ("5 Feb", "TRANSFER IN SPICE ROUTE RESTAURANT", "", "9,800,000.00", "40,550,000.00", ""),
        ("6 Feb", "DEBIT CARD CENDANA FUEL STATION", "720,000.00", "", "39,830,000.00", ""),
        ("9 Feb", "TRANSFER IN DAYBREAK CAFE", "", "18,700,000.00", "58,530,000.00", "lit"),
        ("10 Feb", "VAT PAYMENT JAN", "4,410,000.00", "", "54,120,000.00", ""),
        ("11 Feb", "TRANSFER OUT PRIMEPACK PACKAGING", "3,060,000.00", "", "51,060,000.00", ""),
        ("12 Feb", "INSTANT TRANSFER IN HIGHLAND RESORT &amp; SPA", "", "7,600,000.00", "58,660,000.00", ""),
        ("13 Feb", "TRANSFER OUT ANDI PRATAMA", "5,000,000.00", "", "53,660,000.00", ""),
    ]
    figure = statement_page(page_rows, "01 Feb 2026 to 28 Feb 2026", "Page 1 / 3", "February statement, page 1, with the selected credit highlighted")
    viewer = page_viewer(doc["fileName"], 1, doc["pageCount"], doc["pages"][0]["witness"], figure, lit=True)
    content = f"""
<div class="page stack gap-5">
  {document_header(doc, summary, badges)}
  <div class="doc-layout">{viewer}{pane}</div>
</div>"""
    return shell("documents", topbar(doc["fileName"], ((dw("title"), "documents.html"), doc["fileName"]), back=(dw("title"), "documents.html")), content)


def document_ledger() -> str:
    """A ledger export after import: its rows and period, and the link to the P&L."""
    doc = DOC_FIX["ledger"]
    meta = doc["ledgerMeta"]
    summary = dw("detail.summary.other", type=dw("detail.docType.LEDGER_EXPORT"), uploaded=fmt_date(doc["uploadedAt"][:10]))
    badges = badge(DOC_TYPE_BADGE[doc["docType"]], dw("detail.docType.LEDGER_EXPORT")) + badge("brand", words(DOC_WORDS, "status.done"))
    months_badges = "".join(f'<a class="badge badge-brand" href="month.html">{m}</a>' for m in doc["months"])
    figures = f"""
  <dl class="ledger-figures">
    <div><dt>{dw("detail.rowsImported")}</dt><dd class="v">{meta["rowsImported"]}</dd><dd class="n">{words(DOC_WORDS, "status.imported")}</dd></div>
    <div><dt>{dw("detail.period")}</dt><dd class="v">{fmt_date(meta["dateFrom"])} – {fmt_date(meta["dateTo"])}</dd><dd class="n">{", ".join(doc["months"])}</dd></div>
    <div><dt>{dw("detail.info.type")}</dt><dd class="v">{dw("detail.spreadsheet")}</dd><dd class="n">{doc["contentType"]}</dd></div>
  </dl>"""
    card = f"""
<div class="card stack gap-4">
  <div class="row spread">
    <div><strong>{dw("detail.spreadsheet")}</strong><p class="small muted">{dw("detail.rowsSummary", count=meta["rowsImported"])}</p></div>
    <a class="button button-secondary" href="profit-loss.html">{icon("bar-chart", "icon icon-sm")}<span>{dw("detail.viewProfitLoss")}</span></a>
  </div>
  <div class="row"><span class="muted small">{dw("detail.period")}:</span>{months_badges}</div>
</div>"""
    pane = f"""
<section class="doc-pane" aria-label="{dw("detail.pane")}">
  {figures}
  {doc_tabs([(dw("detail.tabs.ledger"), meta["rowsImported"]), (dw("detail.tabs.details"), None)])}
  <div role="tabpanel" class="stack gap-3">{card}</div>
</section>"""
    content = f"""
<div class="page stack gap-5">
  {document_header(doc, summary, badges)}
  {pane}
</div>"""
    return shell("documents", topbar(doc["fileName"], ((dw("title"), "documents.html"), doc["fileName"]), back=(dw("title"), "documents.html")), content)

def document_ledger_columns() -> str:
    """A ledger export with a new layout: nothing imported yet, the page says so and points to the
    column check in the review queue (spec 005, T005-11)."""
    doc = REVIEW_FIX["documents"]["doc_gl_new"]
    summary = dw("detail.summary.other", type=dw("detail.docType.LEDGER_EXPORT"), uploaded=fmt_date(doc["uploadedAt"][:10]))
    badges = badge(DOC_TYPE_BADGE[doc["docType"]], dw("detail.docType.LEDGER_EXPORT")) + badge("medium", words(DOC_WORDS, "status.needsInput"))
    banner = f"""
  <div class="found" role="status">{icon("table")}<div class="stack gap-1"><strong>{words(DOC_WORDS, "status.needsInput")}</strong><p class="small">{dw("detail.needsColumns")}</p><a class="link small" href="review-mapping.html">{dw("detail.checkColumns")}</a></div></div>"""
    figures = f"""
  <dl class="ledger-figures">
    <div><dt>{dw("detail.rowsImported")}</dt><dd class="v">0</dd><dd class="n">{words(DOC_WORDS, "status.imported")}</dd></div>
    <div><dt>{dw("detail.period")}</dt><dd class="v">—</dd></div>
    <div><dt>{dw("detail.info.type")}</dt><dd class="v">{dw("detail.spreadsheet")}</dd><dd class="n">{doc["contentType"]}</dd></div>
  </dl>"""
    card = f"""
<div class="card stack gap-4">
  <div class="row spread">
    <div><strong>{dw("detail.spreadsheet")}</strong><p class="small muted">{dw("detail.rowsSummary", count=0)}</p></div>
    <a class="button button-secondary" href="profit-loss.html">{icon("bar-chart", "icon icon-sm")}<span>{dw("detail.viewProfitLoss")}</span></a>
  </div>
</div>"""
    pane = f"""
<section class="doc-pane" aria-label="{dw("detail.pane")}">
  {figures}
  {doc_tabs([(dw("detail.tabs.ledger"), 0), (dw("detail.tabs.details"), None)])}
  <div role="tabpanel" class="stack gap-3">{card}</div>
</section>"""
    content = f"""
<div class="page stack gap-5">
  {document_header(doc, summary, badges)}
  {banner}
  {pane}
</div>"""
    return shell("documents", topbar(doc["fileName"], ((dw("title"), "documents.html"), doc["fileName"]), back=(dw("title"), "documents.html")), content)


# ------------------------------------------------------------------------------------------------
# Finance Assistant (P1)
# ------------------------------------------------------------------------------------------------
# Three states of the same screen, with the app's words (assistant.json): a conversation with a
# streaming answer, the welcome state of an empty thread, and the history drawer phones open.

ASSISTANT_WORDS = json.loads((LOCALES / "assistant.json").read_text(encoding="utf-8"))


def aw(key: str, **params) -> str:
    return words(ASSISTANT_WORDS, key, **params)


def assistant_sidebar_markup() -> str:
    """The history rail: New chat, earlier questions and the remembered preferences (docs/11 §6.8)."""
    threads = [
        ("How much did we pay Green Valley Farms in March?", "2 Jul", True),
        ("Why is March critical?", "2 Jul", False),
        ("Show my profit and loss for 2026-03", "2 Jul", False),
        ("Which invoices are still unpaid?", "1 Jul", False),
        ("Where did the money go in Q2?", "28 Jun", False),
    ]
    thread_items = "".join(
        f'<a class="assistant-thread-btn{" is-active" if active else ""}" href="assistant.html">'
        f'<span class="assistant-thread-title">{title}</span><span class="assistant-thread-date">{dt}</span></a>'
        for title, dt, active in threads
    )
    memories = ["Show amounts in millions", "ACB ••5577 is the payroll account", "The financial year starts in January"]
    mem_items = "".join(
        f'<li><span>{mem}</span><button class="link-button small" type="button">{aw("remembered.forget")}</button></li>' for mem in memories
    )
    return f"""
    <a class="button button-primary button-block" href="assistant-welcome.html">{icon("plus", "icon icon-sm")}<span>{aw("newChat")}</span></a>
    <section class="assistant-side-section" aria-labelledby="thr-h">
      <div class="spread"><h2 class="assistant-side-title" id="thr-h">{aw("earlierQuestions")}</h2><span class="badge badge-outline">{len(threads)}</span></div>
      <div class="stack gap-1">{thread_items}</div>
    </section>
    <section class="panel panel-pad stack gap-2 assistant-memory" aria-labelledby="mem-h">
      <div class="spread"><h2 class="assistant-side-title" id="mem-h">{aw("remembered.title")}</h2><button class="link-button small" type="button">{aw("remembered.forgetAll")}</button></div>
      <ul class="remembered">{mem_items}</ul>
      <p class="muted small">{aw("remembered.footer")}</p>
    </section>
"""


def assistant_page_head() -> str:
    return f"""
  <div class="page-head">
    <div class="spread">
      <div class="row">
        <a class="button button-quiet button-sm assistant-history-btn" href="assistant-history.html" aria-label="{aw("history")}">{icon("table", "icon icon-sm")}<span>{aw("history")}</span></a>
        <h1 class="type-title">{aw("title")}</h1>
        <span class="badge badge-outline">{aw("preview")}</span>
      </div>
    </div>
    <p>{aw("subtitle")}</p>
  </div>"""


def assistant_composer() -> str:
    starters = "".join(f'<a href="#">{aw(f"starters.{k}")}</a>' for k in ("unpaid", "flow", "clients"))
    return f"""
      <div class="suggested" aria-label="{aw("suggestedQuestions")}">{starters}</div>
      <form class="composer" action="assistant.html" method="get"><input type="text" placeholder="{aw("composer.placeholder")}" aria-label="{aw("composer.placeholder")}" value=""/><button class="button button-primary" type="submit" aria-label="{aw("composer.send")}">{icon("send", "icon icon-sm")}</button></form>"""


def assistant_layout(main: str) -> str:
    return f"""
<div class="page stack gap-4">
  {assistant_page_head()}
  <div class="assistant-page-container">
    <aside class="assistant-sidebar assistant-sidebar-desktop" aria-label="{aw("recentConversations")}">
      {assistant_sidebar_markup()}
    </aside>
    <main class="assistant-main">
      {main}
      {assistant_composer()}
    </main>
  </div>
</div>"""


def assistant() -> str:
    """A conversation: three grounded answers and a fourth one still being written."""
    grounded = f'<span class="grounded">{icon("shield-check")}{aw("messages.groundingAgreed")}</span>'
    chat = f"""
      <div class="chat">
        <p class="msg-user">How much did we pay Green Valley Farms in March?</p>
        <div class="msg-ai"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="" aria-hidden="true"/>
          <div class="bubble">
            <p>You paid Green Valley Farms <strong>IDR 56,050,000</strong> in March, in 3 transfers <a class="citation" href="month.html">{icon("table")}3 bank lines</a>. All three went to their usual account, ACB ••0912, and each one matches an invoice.</p>
            <div class="mini-bars" role="img" aria-label="Three transfers: 5 Mar 32.1 million, 12 Mar 9.85 million, 26 Mar 14.1 million">
              <div class="mb"><span>5 Mar</span><span class="bar" style="width:100%"></span><b>32.10 M</b></div>
              <div class="mb"><span>12 Mar</span><span class="bar" style="width:31%"></span><b>9.85 M</b></div>
              <div class="mb"><span>26 Mar</span><span class="bar" style="width:44%"></span><b>14.10 M</b></div>
            </div>
            {grounded}
          </div>
        </div>
        <p class="msg-user">Why is March critical?</p>
        <div class="msg-ai"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="" aria-hidden="true"/>
          <div class="bubble">
            <p>Because the March statement looks edited <a class="citation" href="evidence-viewer.html">{icon("eye")}A01</a>. On 14 March it shows IDR 7,250,000 from Harborview Hotel Group, but the balance only rises by IDR 1,250,000, and your ledger and invoice 0009 also say 1,250,000.</p>
            <p>The quickest check is to download March again from internet banking and upload it. Want me to open the evidence?</p>
            <div class="row"><a class="button button-secondary button-sm" href="evidence-viewer.html">{aw("openEvidence")}</a><a class="button button-quiet button-sm" href="month.html">{aw("goToMonth")}</a></div>
            {grounded}
          </div>
        </div>
        <p class="msg-user">Show my profit and loss for 2026-03</p>
        <div class="msg-ai"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="" aria-hidden="true"/>
          <div class="bubble">
            <p>Accrual management P&amp;L from imported posted ledger entries only. These totals do not certify that the company books are complete.</p>
            <div class="mini-bars" role="img" aria-label="Profit and loss for 2026-03">
              <div class="mb"><span>Revenue</span><span class="bar" style="width:100%"></span><b>120.0 M</b></div>
              <div class="mb"><span>Cost of sales</span><span class="bar" style="width:60%"></span><b>72.0 M</b></div>
              <div class="mb"><span>Gross profit</span><span class="bar" style="width:40%"></span><b>48.0 M</b></div>
              <div class="mb"><span>Operating expenses</span><span class="bar" style="width:15%"></span><b>18.0 M</b></div>
              <div class="mb"><span>Net profit</span><span class="bar" style="width:22%"></span><b>26.0 M</b></div>
            </div>
            <p>Net profit: IDR 26,000,000 <a class="citation" href="profit-loss.html">Net profit</a></p>
            <div class="row"><a class="button button-secondary button-sm" href="profit-loss.html">Open profit and loss</a></div>
            {grounded}
          </div>
        </div>
        <p class="msg-user">Who are my biggest clients?</p>
        <div class="msg-ai" data-testid="streaming-ai-message"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="" aria-hidden="true"/>
          <div class="bubble stack gap-3">
            <div class="activity-trail is-running" data-testid="activity-trail">
              <button class="trail-head" type="button" aria-expanded="true" aria-label="{aw("activity.toggle")}">{icon("spinner", "icon icon-sm spin")}<span>{aw("activity.running")}</span>{icon("chevron-up", "icon icon-sm")}</button>
              <ul class="trail-list" aria-live="polite">
                <li class="trail-item">{icon("check", "icon icon-sm")}<span>Reading the period's money flow</span></li>
                <li class="trail-item is-busy">{icon("spinner", "icon icon-sm spin")}<span>Listing clients by money in</span></li>
              </ul>
            </div>
            <div class="thinking-dots" aria-label="{aw("activity.thinking")}"><span></span><span></span><span></span></div>
          </div>
        </div>
      </div>"""
    return shell("assistant", topbar(aw("title"), (aw("title"),)), assistant_layout(chat), fab=False)


def assistant_welcome_markup() -> str:
    prompts = [("bar-chart", "flow", "flow"), ("file-text", "unpaid", "unpaid"), ("shield-alert", "risk", "risk"), ("table", "pnl", "pnl")]
    cards = "".join(
        f'<a class="assistant-prompt-card" href="assistant.html"><span class="assistant-prompt-card-icon">{icon(ic, "icon icon-sm")}</span>'
        f'<span class="assistant-prompt-card-text"><strong>{aw(f"welcome.prompts.{title}")}</strong><span>{aw(f"starters.{question}")}</span></span></a>'
        for ic, title, question in prompts
    )
    return f"""
      <div class="chat">
        <div class="assistant-welcome" data-testid="assistant-welcome">
          <div class="assistant-welcome-hero">
            <img class="assistant-welcome-mark" src="{BRAND}/kredibel-mark.svg" alt="" aria-hidden="true"/>
            <h2 class="assistant-welcome-title">{aw("welcome.title")}</h2>
            <p class="assistant-welcome-subtitle">{aw("welcome.subtitle")}</p>
          </div>
          <div class="assistant-suggestion-grid">{cards}</div>
        </div>
      </div>"""


def assistant_welcome() -> str:
    """An empty thread: the welcome prompts a person can start from."""
    return shell("assistant", topbar(aw("title"), (aw("title"),)), assistant_layout(assistant_welcome_markup()), fab=False)


def assistant_history() -> str:
    """The history drawer phones open from the Chat history button (the rail from 900 px)."""
    drawer = f"""
<div class="flow-sheet">
  <a class="scrim" href="assistant-welcome.html" aria-label="{aw("closeHistory")}"></a>
  <section class="sheet" role="dialog" aria-modal="true" aria-label="{aw("history")}">
    <div class="sheet-head">
      <h2 class="type-h3">{aw("recentConversations")}</h2>
      <a class="icon-button" href="assistant-welcome.html" aria-label="{aw("closeHistory")}">{icon("x")}</a>
    </div>
    <div class="sheet-body stack gap-3">{assistant_sidebar_markup()}</div>
  </section>
</div>"""
    return shell("assistant", topbar(aw("title"), (aw("title"),)), assistant_layout(assistant_welcome_markup()) + drawer, fab=False)

# ------------------------------------------------------------------------------------------------
# Plan and usage (Settings)
# ------------------------------------------------------------------------------------------------

def plan_usage() -> str:
    track = "".join(f'<i class="{"used" if i < 7 else ""}"></i>' for i in range(30))
    meters = [
        ("Documents this month", "92", "150", 61, "Exact copies don't count.", False),
        ("Pages read this month", "286", "400", 72, "114 pages left. Re-uploaded pages are free.", False),
        ("AI use this month", "USD 1.84", "USD 5.00", 37, "Estimated from pages read and questions asked.", False),
        ("Month reconciliations today", "52", "60", 87, "Close to today's limit. New uploads wait until tomorrow.", True),
        ("Team members", "1", "3", 33, "Team roles are coming soon.", False),
        ("Assistant questions today", "6", "50", 12, "", False),
    ]
    mt = "".join(f"""<div class="meter{' is-near' if near else ''}"><div class="m-top"><span>{label}</span><strong>{used} <small>of {mx}</small></strong></div><div class="meter-bar"><i style="width:{pct}%"></i></div><p class="m-note">{note}</p></div>""" for label, used, mx, pct, note, near in meters)
    def plan(name, price, items, current=False):
        cls = "plan is-current" if current else "plan is-soon"
        badge = '<span class="badge badge-brand">Your plan</span>' if current else '<span class="badge badge-outline">Coming soon</span>'
        lis = "".join(f'<li>{icon("check", "icon icon-sm")}{t}</li>' for t in items)
        btn = '<a class="button button-secondary button-block" href="#">See limits</a>' if current else '<button class="button button-block" disabled>Not available yet</button>'
        return f'<div class="{cls}"><div class="plan-head">{badge}<h3>{name}</h3><p class="muted small">{price}</p></div><ul>{lis}</ul><div class="plan-foot">{btn}</div></div>'
    plans = "".join([
        plan("Free trial", "Free for 30 days", ["Every feature of the prototype", "Team invites coming soon", "400 pages read per month"], True),
        plan("Starter", "Pricing announced later", ["More documents and pages", "Up to 10 team members", "Email support"]),
        plan("Professional", "Pricing announced later", ["A second reader on every page", "Several workspaces for a firm", "Audit export"]),
        plan("Enterprise", "Contact us later", ["Processing in your region", "Single sign-on", "Custom limits"]),
    ])
    content = f"""
<div class="page">
  <div class="page-head"><h1 class="type-title">Settings</h1></div>
  <div class="settings-layout">
    <nav class="subnav" aria-label="Settings sections"><a href="#">Profile</a><a href="#">Bank accounts</a><a href="#">Language and formats</a><a href="#" aria-current="page">Plan and usage</a><a href="#">Team (soon)</a></nav>
    <div class="stack gap-8">
      <section class="trial-hero" aria-labelledby="trial-h">
        <div><p class="days" id="trial-h">23<small>days left</small></p></div>
        <div class="stack gap-3"><p>Your free trial ends on 2 Nov 2026. After that you can still read your books and fix review items; new uploads pause until paid plans open.</p><div class="trial-track" role="img" aria-label="Day 7 of 30">{track}</div></div>
      </section>
      <section aria-labelledby="use-h" class="meters-wrap">
        <div class="section-head"><h2 class="type-h2" id="use-h">Usage</h2><p>Counted in UTC. Limits reset on the 1st.</p></div>
        <div class="meters">{mt}</div>
      </section>
      <section aria-labelledby="plans-h" class="plans-wrap stack gap-4">
        <div class="section-head"><h2 class="type-h2" id="plans-h">Plans</h2><p>Paid plans are not available yet. Nothing here can start a payment.</p></div>
        <div class="plans">{plans}</div>
        <div class="soon-features">
          <div class="soon"><span class="ico">{icon("book")}</span><div><div class="row"><h3>Loan readiness report</h3><span class="badge badge-outline">Coming soon</span></div><p>A lender-ready summary of your verified months, built on the same checked data.</p></div></div>
          <div class="soon"><span class="ico">{icon("bank")}</span><div><div class="row"><h3>Bank feeds</h3><span class="badge badge-outline">Coming soon</span></div><p>Statements arrive by themselves instead of by upload.</p></div></div>
        </div>
      </section>
    </div>
  </div>
</div>"""
    return shell("settings", topbar("Plan and usage", (("Settings", "plan-usage.html"), "Plan and usage"), back=("Dashboard", "dashboard.html")), content, fab=False)


SETTINGS_WORDS = json.loads((LOCALES / "settings.json").read_text(encoding="utf-8"))
ONBOARD_WORDS = json.loads((LOCALES / "onboarding.json").read_text(encoding="utf-8"))


def sw(key: str, **params) -> str:
    return words(SETTINGS_WORDS, key, **params)


def settings_frame(current: str, body: str) -> str:
    """The Settings page head and section subnav around one section (SettingsPage)."""
    links = []
    for key, label in SETTINGS_WORDS["sections"].items():
        if key == "members":
            links.append(f'<a role="link" aria-disabled="true" class="cursor-default">{escape(label)}</a>')
        else:
            links.append(f'<a href="#"{" aria-current=\"page\"" if key == current else ""}>{escape(label)}</a>')
    return f"""
<div class="page">
  <div class="page-head"><h1 class="type-title">{sw("title")}</h1></div>
  <div class="settings-layout">
    <nav class="subnav" aria-label="{sw("sectionsLabel")}">{"".join(links)}</nav>
    {body}
  </div>
</div>"""


def settings_profile() -> str:
    """Settings › Profile (ProfileForm): the synthetic workspace, IFRS chosen (AC-013-14, AC-016-8)."""
    opt = f'<span class="muted">({sw("profile.optional")})</span>'
    legal_forms = "".join(f'<option value="{k}">{escape(v)}</option>' for k, v in SETTINGS_WORDS["profile"]["legalForms"].items())
    industries = "".join(f"<option>{escape(v)}</option>" for v in ONBOARD_WORDS["industries"].values())
    frameworks = seg("framework", [(k, sw(f"profile.frameworks.{k}")) for k in ("IFRS", "US_GAAP")], "IFRS", sw("profile.framework"))
    form = f"""
<form class="panel panel-pad stack gap-6" novalidate>
  <p class="muted">{sw("profile.intro")}</p>
  <div class="form-wrap">
    <div class="form-grid">
      <div class="field"><span class="label">{sw("profile.type")}</span><span>{sw("entityTypes.COMPANY")}</span><span class="hint">{sw("profile.typeFixed")}</span></div>
      <div class="field"><span class="label">{sw("language.currency")}</span><span class="row gap-2 font-medium">Indonesian Rupiah (IDR)<span class="badge badge-outline">{sw("plan.comingSoon")}</span></span><span class="hint">{sw("language.currencyFixed")}</span></div>
      <div class="field span-2"><span class="label" id="framework-l">{sw("profile.framework")}</span>{frameworks}<span class="hint">{sw("profile.frameworkHint")}</span></div>
      <div class="field span-2"><span class="label">{sw("profile.goal")}</span><span class="row gap-2">{sw("profile.goals.BOOKKEEPING")}<a class="link" href="welcome.html">{sw("profile.changeGoal")}</a></span><span class="hint">{sw("profile.goalHint")}</span></div>
      <div class="field span-2"><label for="name">{sw("profile.legalName")}</label><input class="input" id="name" value="Sunrise Coffee Roasters"/></div>
      <div class="field"><label for="tradingName">{sw("profile.tradingName")} {opt}</label><input class="input" id="tradingName"/></div>
      <div class="field"><label for="legalForm">{sw("profile.legalForm")} {opt}</label><select class="select" id="legalForm"><option value="">{sw("profile.chooseLegalForm")}</option>{legal_forms}</select></div>
      <div class="field"><label for="industry">{sw("profile.industry")} {opt}</label><select class="select" id="industry"><option value="">{words(ONBOARD_WORDS, "industryChoose")}</option>{industries}</select></div>
      <div class="field"><label for="taxId">{sw("profile.taxId")} {opt}</label><input class="input" id="taxId" autocomplete="off"/><span class="hint">{sw("profile.taxIdHint")}</span></div>
      <div class="field span-2"><label for="line1">{sw("profile.addressLine")} {opt}</label><input class="input" id="line1"/></div>
      <div class="field"><label for="city">{sw("profile.city")} {opt}</label><input class="input" id="city"/></div>
      <div class="field"><label for="timezone">{sw("profile.timeZone")}</label><select class="select" id="timezone"><option>Asia/Jakarta (UTC+07:00)</option></select></div>
      <div class="field span-2"><label for="aliases">{sw("profile.aliases")} {opt}</label><textarea class="textarea" id="aliases"></textarea><span class="hint">{sw("profile.aliasesHint")}</span></div>
    </div>
  </div>
  <div class="row"><button type="submit" class="button button-primary">{sw("profile.save")}</button></div>
</form>"""
    return shell("settings", topbar(sw("sections.profile"), ((sw("title"), "plan-usage.html"), sw("sections.profile")), back=("Dashboard", "dashboard.html")), settings_frame("profile", f'<div class="stack gap-6">{suggestion_card("settings")}{form}</div>'), fab=False)


# ------------------------------------------------------------------------------------------------
# Onboarding
# ------------------------------------------------------------------------------------------------

def onboard_brand() -> str:
    return f"""
<section class="onboard-brand" aria-label="Kredibel">
  <img class="logo" src="{BRAND}/kredibel-logo-on-dark.svg" alt="Kredibel"/>
  <div class="stack gap-6">
    <p class="tagline">Every number has a source.</p>
    <ul class="promise">
      <li>{icon("copy")}<span>Send the same file twice and it is never counted twice.</span></li>
      <li>{icon("ai-reader")}<span>Every number is read twice before it counts, and you can see where it came from.</span></li>
      <li>{icon("reconcile")}<span>Months reconcile themselves, in any upload order. You only fix what is left.</span></li>
    </ul>
  </div>
  <div class="ledger" aria-hidden="true">
    <div class="ledger-line"><span>05 Mar</span><span class="desc">TRANSFER OUT GREEN VALLEY FARMS</span><span class="amt"><span class="reading reading-agreed">32,100,000</span> <span class="tick">{icon("ai-reader", "icon icon-sm")}read twice</span></span></div>
    <div class="ledger-line"><span>11 Mar</span><span class="desc">TRANSFER IN DAYBREAK CAFE</span><span class="amt">6,420,000 <span class="tick">{icon("check", "icon icon-sm")}matched</span></span></div>
    <div class="ledger-line"><span>12 Mar</span><span class="desc">ACB_Feb_2026 (1).pdf</span><span class="amt"><span class="tick dup">{icon("copy", "icon icon-sm")}copy, not read</span></span></div>
  </div>
  <p class="small-print">Kredibel only reads your documents. It never moves money and never changes your accounting system.</p>
</section>"""


def onboarding() -> str:
    brand = onboard_brand()
    form = f"""
<section class="onboard-form" aria-labelledby="ob-h">
  <div class="stack gap-2"><h1 class="type-title" id="ob-h">Set up your business</h1><p class="muted">One workspace is one business. You can add details later; Kredibel will suggest them from your documents.</p></div>
  <section class="onboard-demo" aria-labelledby="demo-h">{icon("sparkles")}<div class="stack gap-1"><h2 id="demo-h">{words(ONBOARD_WORDS, "demo.title")}</h2><p>{words(ONBOARD_WORDS, "demo.body")}</p></div><div class="actions"><a class="button button-secondary" href="tour.html">{words(ONBOARD_WORDS, "demo.open")}</a></div></section>
  <p class="onboard-or">{words(ONBOARD_WORDS, "demo.or")}</p>
  <section class="form-section" aria-labelledby="ob-biz"><h2 id="ob-biz">Your business</h2><div class="form-wrap"><div class="form-grid">
    <div class="field span-2"><label for="n">Legal name</label><input class="input" id="n" value="Sunrise Coffee Roasters"/></div>
    <div class="field"><label for="t">Trading name <span class="muted">(optional)</span></label><input class="input" id="t" placeholder="As on your invoices"/></div>
    <div class="field"><label for="f">Legal form</label><select class="select" id="f"><option>Partnership</option></select></div>
    <div class="field"><label for="i">Industry</label><select class="select" id="i"><option>Food and drink, wholesale</option></select></div>
    <div class="field"><label for="x">Tax ID <span class="muted">(optional)</span></label><input class="input" id="x" placeholder="Stored masked"/></div>
  </div></div></section>
  <section class="form-section" aria-labelledby="ob-books"><h2 id="ob-books">Your books</h2><div class="form-wrap"><div class="form-grid">
    <div class="field"><label for="c">Currency</label><select class="select" id="c"><option>Indonesian Rupiah (IDR)</option></select><span class="hint">The currency of your books. Changing it later is coming soon.</span></div>
    <div class="field"><label for="z">Time zone</label><select class="select" id="z"><option>Asia/Jakarta (UTC+7)</option></select><span class="hint">Months are counted in this time zone.</span></div>
    <div class="field span-2"><span class="label" id="fw-l">Accounting framework</span>{seg("obfw", [("IFRS", "IFRS"), ("US_GAAP", "US GAAP")], "IFRS", "Accounting framework")}<span class="hint">How cash flows are grouped on your dashboard. You can switch the view any time.</span></div>
  </div></div></section>
  <details class="disclosure"><summary><span>Main bank account<span class="opt">optional</span></span>{icon("chevron-down")}</summary></details>
  <p class="trial-note">{icon("clock")}<span><strong>30-day free trial.</strong> 150 documents and 400 pages a month. No card, no payment. Paid plans are coming soon.</span></p>
  <a class="button button-primary button-lg button-block" href="documents.html">Start the free trial</a>
</section>"""
    return f'<div class="viewport"><div class="onboard">{brand}{form}</div></div>'


def welcome(expect: bool = False) -> str:
    """Spec 024: the welcome question after onboarding (WelcomePage), with no navigation."""
    def ow(key: str, **params) -> str:
        return words(ONBOARD_WORDS, f"welcome.{key}", **params)

    def card(kind: str, glyph: str, attrs: str) -> str:
        return (f'<button type="button" class="welcome-choice"{attrs}>{icon(glyph)}<span class="stack gap-1">'
                f'<span class="w-t">{ow(kind + ".title")}</span><span class="w-b">{ow(kind + ".body")}</span></span></button>')

    expanded = "true" if expect else "false"
    form = ""
    if expect:
        rows = ""
        for i, (month, money_in, money_out) in enumerate([("2026-09", "150000000", "120000000"), ("2026-10", "160000000", "")]):
            rows += (f'<div class="expect-row" role="group" aria-label="{ow("form.rowAria", index=i + 1)}">'
                     f'<div class="field"><label for="exp-month-{i}">{ow("form.month")}</label><input class="input" id="exp-month-{i}" type="month" value="{month}"/></div>'
                     f'<div class="field"><label for="exp-in-{i}">{ow("form.moneyIn")}</label><input class="input n" id="exp-in-{i}" inputmode="numeric" value="{money_in}"/></div>'
                     f'<div class="field"><label for="exp-out-{i}">{ow("form.moneyOut")}</label><input class="input n" id="exp-out-{i}" inputmode="numeric" value="{money_out}"/></div>'
                     f'<button type="button" class="button button-quiet button-sm expect-remove" aria-label="{ow("form.remove", month=month_name(month))}">{icon("x", "icon icon-sm")}</button></div>')
        form = f"""
  <form class="form-section stack gap-4" aria-labelledby="welcome-form-h">
    <h2 id="welcome-form-h">{ow("form.title")}</h2>
    <div class="expect-rows"><p class="hint">{ow("form.hint", currency="IDR")}</p>{rows}</div>
    <div class="actions"><button type="button" class="button button-secondary">{icon("plus", "icon icon-sm")}{ow("form.add")}</button></div>
    <a class="button button-primary button-lg button-block" href="dashboard-expectations.html">{ow("form.save")}</a>
  </form>"""
    section = f"""
<section class="onboard-form" aria-labelledby="welcome-h">
  <div class="stack gap-2"><h1 class="type-title" id="welcome-h">{ow("title")}</h1><p class="muted">{ow("subtitle")}</p></div>
  <div class="welcome-choices">{card("books", "reconcile", "")}{card("expect", "scale", f' aria-expanded="{expanded}"')}</div>{form}
  <a class="button button-quiet welcome-skip" href="dashboard.html">{ow("skip")}</a>
</section>"""
    return f'<div class="viewport"><div class="onboard">{onboard_brand()}{section}</div></div>'



TX_WORDS = json.loads((LOCALES / "transactions.json").read_text(encoding="utf-8"))
TX_FIX = json.loads((ROOT / "contracts/design/fixtures/transactions.json").read_text(encoding="utf-8"))
TX_CHIP = {"AUTO": ("auto", "link"), "MANUAL": ("manual", "hand"), "PROPOSED": ("proposed", "eye"),
           "UNMATCHED": ("none", "file-text"), "EXCLUDED": ("excluded", "refresh")}
TX_MARK = {"AGREED": "reading-agreed", "SINGLE_SOURCE": "reading-single", "CONFLICT": "reading-conflict", "MISSING": "reading-conflict"}
TX_RECORD_ICON = {"INVOICE": "file-text", "RECEIPT": "receipt", "LEDGER_ENTRY": "book"}


def txw(key: str, **params) -> str:
    return words(TX_WORDS, key, **params)


def tx_by(tx: dict) -> str:
    """widgets/transactions/categorizedBy.ts: a person, the match, a rule, or the model and its confidence."""
    by = tx.get("categorizedBy") or "NONE"
    if by == "MODEL":
        conf = tx.get("categoryConfidence")
        return txw("by.MODEL", confidence=round(float(conf) * 100)) if conf else txw("by.MODEL_plain")
    return txw(f"by.{by}")


def tx_amount(tx: dict) -> str:
    value = tx["amount"]["amount"]
    incoming = not value.startswith("-")
    return (f'<span class="{"amt-in" if incoming else "amt-out"}"><span class="reading {TX_MARK[tx["reading"]]}">'
            f'{"+" if incoming else ""}{amount(value)}</span></span>')


def tx_chip(tx: dict) -> str:
    chip, glyph = TX_CHIP.get(tx["match"]["state"], TX_CHIP["UNMATCHED"])
    return f'<span class="match-chip {chip}">{icon(glyph, "icon icon-sm")}<span>{txw("match." + tx["match"]["state"])}</span></span>'


def transactions(selected: str | None = None) -> str:
    """The Transactions table (spec 024), as pages/TransactionsPage.tsx, from the shared fixture."""
    items = TX_FIX["items"]
    page = items[:10]  # TransactionsPage: ten rows a page, as every table
    trs = []
    for tx in page:
        first = tx["description"].split("\n")[0]
        party = tx.get("counterpartyName")
        desc = f'<strong>{escape(party or first)}</strong>' + (f'<span class="reason">{escape(first)}</span>' if party else "")
        records = ", ".join(txw(f"records.{r['kind']}", label=r["label"]) for r in tx["match"]["records"])
        sel = tx["txId"] == selected
        trs.append(f"""<tr class="is-clickable{" is-selected" if sel else ""}"{' aria-selected="true"' if sel else ""} tabindex="0">
  <td>{fmt_date(tx["date"])}</td>
  <td data-cell="wide"><div class="stack gap-1">{desc}</div></td>
  <td class="r">{tx_amount(tx)}</td>
  <td><div class="stack gap-1"><span>{escape(tx["categoryLabel"])}</span><span class="reason">{tx_by(tx)}</span></div></td>
  <td class="hide-rt small" data-cell="hide">{txw("classes." + tx["cashflow"]["ifrs"])}</td>
  <td class="hide-rt small" data-cell="hide">{txw("classes." + tx["cashflow"]["usGaap"])}</td>
  <td class="hide-rt small" data-cell="hide"><div class="stack gap-1"><span>{escape(tx.get("subledger") or "—")}</span>{f'<span class="reason">{escape(tx["pnlLine"])}</span>' if tx.get("pnlLine") else ""}</div></td>
  <td class="hide-rt small" data-cell="hide">{txw("reading." + tx["reading"])}</td>
  <td><div class="stack gap-1">{tx_chip(tx)}{f'<span class="reason">{escape(records)}</span>' if records else ""}</div></td>
</tr>""")
    states = ["AUTO", "MANUAL", "PROPOSED", "UNMATCHED"]
    filters = [(txw("filters.all"), len(items))] + [(txw(f"filters.{s}"), sum(1 for tx in items if tx["match"]["state"] == s)) for s in states]
    columns = [(txw("columns.date"), ""), (txw("columns.description"), "wide"), (txw("columns.amount"), "r"), (txw("columns.category"), ""),
               (txw("columns.ifrs"), "hide small"), (txw("columns.usGaap"), "hide small"), (txw("columns.subledger"), "hide small"),
               (txw("columns.reading"), "hide small"), (txw("columns.match"), "")]
    picker = f'<select class="select select-sm" aria-label="{txw("month")}"><option selected>{month_name(TX_FIX["month"])}</option></select>'
    table = data_table(filters, 0, txw("filters.label"), txw("search"), columns, "".join(trs), actions=picker,
                       pager=words(COMMON_WORDS, "table.showingRange", **{"from": 1, "to": len(page), "total": len(items)}), table_class="tx-table",
                       pages=(1, -(-len(items) // 10)))
    drawer = transaction_drawer(next(tx for tx in items if tx["txId"] == selected)) if selected else ""
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">{txw("title")}</h1>
    <p>{txw("subtitle")}</p>
  </div>
  {table}
  {drawer}
</div>"""
    return shell("transactions", topbar(txw("title"), (txw("title"),)), content)


def transaction_drawer(tx: dict) -> str:
    """One transaction in the kit's drawer, as widgets/transactions/TransactionDrawer.tsx."""
    value = tx["amount"]["amount"]
    incoming = not value.startswith("-")
    facts = [(txw("drawer.date"), fmt_date(tx["date"])), (txw("drawer.category"), f'{escape(tx["categoryLabel"])} ({tx_by(tx)})'),
             (txw("drawer.ifrs"), txw("classes." + tx["cashflow"]["ifrs"])), (txw("drawer.usGaap"), txw("classes." + tx["cashflow"]["usGaap"])),
             (txw("drawer.pnl"), escape(tx.get("pnlLine") or "—")), (txw("drawer.subledger"), escape(tx.get("subledger") or "—")),
             (txw("drawer.reading"), txw("reading." + tx["reading"]))]
    dl = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts)
    records = tx["match"]["records"]
    recs = (f'<p class="muted small">{txw("drawer.nothing")}</p>' if not records else
            '<ul class="tx-records">' + "".join(
                f'<li><a class="link" href="document.html">{icon(TX_RECORD_ICON[r["kind"]], "icon icon-sm")}{escape(txw("records." + r["kind"], label=r["label"]))}</a></li>'
                for r in records) + "</ul>")
    sub = escape(tx.get("counterpartyName") or month_name(tx["month"]))
    return f"""
<div class="drawer-frame">
  <div class="drawer-behind" aria-hidden="true"></div>
  <div class="drawer" role="dialog" aria-modal="true" aria-labelledby="tx-h">
    <div class="drawer-head">
      <div class="stack gap-2 flex-1 min-w-0">
        <span class="muted small">{sub}</span>
        <h1 id="tx-h">{escape(tx["description"].split(chr(10))[0])}</h1>
        <p class="{"amt-in" if incoming else "amt-out"}"><span class="reading {TX_MARK[tx["reading"]]}">{"+" if incoming else ""}{amount(value)}</span> <small>{tx["amount"]["currency"]}</small></p>
      </div>
      <a class="icon-button" href="transactions.html" aria-label="{txw("drawer.close")}">{icon("x")}</a>
    </div>
    <div class="drawer-body tx-body">
      <dl class="tx-facts">{dl}</dl>
      <section class="stack gap-2" aria-labelledby="tx-matched-h">
        <h2 id="tx-matched-h" class="small muted">{txw("drawer.matchedTo")}</h2>
        {tx_chip(tx)}
        {recs}
      </section>
      <div class="actions">
        <a class="button button-secondary button-sm" href="document.html">{icon("file-text", "icon icon-sm")}{txw("drawer.statement")}</a>
        <a class="button button-quiet button-sm" href="month.html">{txw("drawer.month")}</a>
      </div>
    </div>
  </div>
</div>"""

SCREENS = {
    "dashboard": ("Dashboard", dashboard),
    "profit-loss": ("Company profit and loss", profit_loss),
    "documents": ("Documents", documents),
    "document": ("Document", document),
    "document-ledger": ("Document: ledger export", document_ledger),
    "document-ledger-columns": ("Document: ledger export awaiting its columns", document_ledger_columns),
    "month": ("Month reconciliation", month),
    "months": ("All months", months),
    "reconciliation": ("Bank evidence and document support", reconciliation),
    "review": ("Review queue", review),
    "review-match": ("Review: choose a match", review_match),
    "review-correction": ("Review: check a value", review_correction),
    "review-mapping": ("Review: check columns", review_mapping),
    "review-type": ("Review: choose the type", review_type),
    "evidence-viewer": ("Evidence viewer", evidence_viewer),
    "assistant": ("Finance Assistant", assistant),
    "assistant-welcome": ("Finance Assistant: welcome", assistant_welcome),
    "assistant-history": ("Finance Assistant: history drawer", assistant_history),
    "plan-usage": ("Plan and usage", plan_usage),
    "settings-profile": ("Settings: profile", settings_profile),
    "onboarding": ("Onboarding", onboarding),
    "welcome": ("Welcome", welcome),
    "welcome-expect": ("Welcome: expectations", lambda: welcome(expect=True)),
    "dashboard-expectations": ("Dashboard: expectations", lambda: dashboard(expectations=True)),
    "transactions": ("Transactions", transactions),
    "transaction": ("Transactions: one transaction", lambda: transactions(selected="st-05#6")),
    "tour": ("Guided tour", tour),
}

NOTES = {
    "profit-loss": "Accrual management P&L from posted ledger activity, with company account classifications and source rows.",
    "dashboard": "The period's figures, the profit and loss panel, then full-width charts grouped by IFRS or US GAAP: money flow (flow, bars, table or by client and supplier), money in and out by month, and the cash-flow statement. Below, one sentence says where the books stand, then the open risks, what is to review and where the money went in short, and the months.",
    "document": "One read document: the page viewer with the selected value lit, beside what was read from it, a paginated list with reading marks, its findings and details.",
    "document-ledger": "A ledger export after import: rows and period, and the link to the profit and loss.",
    "document-ledger-columns": "A ledger export with a new layout: nothing imported yet, the page says so and points to the column check.",
    "review-mapping": "A ledger export with a new layout: which column of the file holds each field, the first rows as read, confirmed once per layout.",
    "months": "All months in one table: state, risk and statements, newest first; each row opens its month.",
    "review-match": "The fix drawer for a proposed match: the bank line, the invoice it fits, why, and Confirm the match.",
    "review-correction": "A value to check: the receipt beside the panel, the correction form open.",
    "documents": "Upload anything in any order. Exact copies are recognised at once; possible copies wait for you; ledgers ask for their columns once.",
    "month": "One month's reconciliation: the figures, the explained risk with its citations and next steps, the match meter, and every bank line with its category, support and action.",
    "reconciliation": "A separate synthetic MYR workspace preview: grouped and split payments, bank-only rows, documents before statements, separate approval/payment confirmation and currency agreement without conversion.",
    "review": "One queue for everything AI could not settle, in the shared table with chips by kind; an item opens the fix drawer.",
    "evidence-viewer": "The lamp on the printed value, the calculation, and both readings side by side. Phones open zoomed to the evidence.",
    "assistant": "Questions about your books, answered from tools with citations and a small chart, with the history rail and an answer being written; only preferences are remembered.",
    "assistant-welcome": "An empty thread: the welcome prompts to start from, the history rail and the composer.",
    "assistant-history": "The history drawer phones open from the Chat history button; wide screens show the rail instead.",
    "plan-usage": "Trial days, usage that warns before a limit, coming-soon plans and features that cannot be clicked.",
    "settings-profile": "The profile form with the accounting framework that sets the cash-flow classes; changing it reclassifies every month.",
    "onboarding": "The demo company when the server has one, then the business in one form; the brand panel explains the promise with a ledger.",
    "welcome": "Spec 024: asked once after onboarding, with no navigation: keep the books, or check what you expect first.",
    "welcome-expect": "Spec 024: the money in and out expected per month; empty means unknown. Saved, then the dashboard.",
    "dashboard-expectations": "Spec 024: the dashboard with what the person expected against the reconciled months, and the way to each month and its transactions and documents.",
    "transactions": "Spec 024: every bank line of a month in one table, with its category and who chose it, its cash-flow class under IFRS and US GAAP, its subledger, its reading and what it is matched to.",
    "transaction": "Spec 024: one transaction in the drawer, with its classes, reading, matched records and the way to its statement and month.",
    "tour": "The guided tour on the dashboard: the figures lit, the page dimmed around them, and the card with Back, Next and Skip.",
}
