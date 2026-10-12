"""Kredibel 2.1 screen mocks (finance workspace). Each function returns the body markup.
Synthetic data: the demo workspace of docs/18 (Sunrise Coffee Roasters, Jan–Jun 2026, scenarios S1 to S4
together: the edited March statement, the duplicates, the changed supplier account and the unpaid bills)."""

from icons import icon
from shell import shell, topbar, BRAND
from sankey import sankey_svg, flow_list, flow_table
import charts

SEV = {"critical": ("octagon-alert", "Critical"), "high": ("triangle-alert", "High"),
       "medium": ("circle-alert", "Medium"), "low": ("info", "Low")}


def sev_badge(level: str) -> str:
    ic, label = SEV[level]
    return f'<span class="badge badge-{level}">{icon(ic)}{label}</span>'


# ------------------------------------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------------------------------------

MONTHS = [
    ("Jan", "ok", "Reconciled", "low", 94, "42 of 45", "Statement, ledger"),
    ("Feb", "wait", "2 need you", "medium", 89, "40 of 45", "Possible copy held"),
    ("Mar", "wait", "2 need you", "critical", 86, "39 of 45", "Statement edited"),
    ("Apr", "ok", "Reconciled", "low", 93, "42 of 45", "Statement, ledger"),
    ("May", "wait", "3 need you", "high", 88, "40 of 45", "Supplier account changed"),
    ("Jun", "wait", "2 need you", "medium", 87, "39 of 45", "Possible copy held"),
]


def month_tabs() -> str:
    out = []
    for m, state, label, risk, pct, of, note in MONTHS:
        cls = {"critical": " is-critical", "high": " is-high", "medium": " is-open"}.get(risk, "")
        st_icon = "check-circle" if state == "ok" else "inbox"
        out.append(f"""<li><a class="mtab{cls}" href="month.html">
  <span class="m-name"><strong>{m}</strong><span>2026</span></span>
  <span class="m-state {state}">{icon(st_icon)}{label}</span>
  <span class="m-matched"><span><b>{pct}%</b> matched by Kredibel</span><span class="meter-bar"><i style="width:{pct}%"></i></span><span>{of} bank lines</span></span>
  <span class="m-foot">{sev_badge(risk)}<span>{note}</span></span>
</a></li>""")
    return f'<div class="months-wrap"><ol class="months">{"".join(out)}</ol></div>'


TODOS = [
    ("match", "link", "IDR 7,250,000 on 14 Mar differs from your ledger", "Harborview Hotel Group; the March statement looks edited"),
    ("dup", "copy", "Possible copy of the February statement", "ACB_Feb_2026 (re-download).pdf has the same 45 lines"),
    ("match", "link", "IDR 18,700,000 on 9 Feb fits two invoices", "Daybreak Café, invoices 0003 and 0004"),
    ("doc", "file-text", "Two Bluewater Trading Co. invoices never paid", "No bank line or ledger entry for either"),
    ("doc", "wallet", "Cash deposit of IDR 2,150,000 is not in the ledger", "21 Jun, ACB ••4821"),
]


def todo_list(n=5) -> str:
    items = "".join(
        f'<li><a class="todo" href="review.html"><span class="kind {k}">{icon(ic)}</span><span><span class="t">{t}</span><br/><span class="s">{s}</span></span><span class="go">{icon("chevron-right")}</span></a></li>'
        for k, ic, t, s in TODOS[:n])
    return f'<ul class="todo-list">{items}</ul>'


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


def dashboard() -> str:
    hero = f"""
<section class="status-hero" aria-labelledby="status-h">
  <p class="greeting">Sunrise Coffee Roasters, January to June 2026</p>
  <h1 class="status-sentence" id="status-h"><span class="done">2 of 6 months are reconciled.</span> <span class="ask">9 things need you.</span></h1>
  <ul class="why">
    <li><span class="sev-critical">{icon("octagon-alert")}</span><span><strong>March:</strong> the bank statement was edited after the bank issued it.</span></li>
    <li><span class="sev-high">{icon("triangle-alert")}</span><span><strong>May:</strong> a supplier was paid to a bank account we have not seen for them before.</span></li>
  </ul>
  <div class="actions"><a class="button button-primary button-lg" href="review.html">{icon("inbox", "icon icon-sm")}Open review (9)</a><a class="button button-secondary button-lg" href="month.html">See March</a></div>
</section>"""
    figs = f"""
<section class="ledger" aria-label="Figures for January to June 2026">
  <dl class="ledger-figures">
    <div><dt>{icon("arrow-down-left", "icon icon-sm")}Money in</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">1,355.8 M</span></dd><dd class="n">226.0 M a month on average</dd></div>
    <div><dt>{icon("arrow-up-right", "icon icon-sm")}Money out</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">1,286.8 M</span></dd><dd class="n">214.5 M a month on average</dd></div>
    <div><dt>Net</dt><dd class="v"><small>IDR</small>+69.0 M</dd><dd class="n up">Kept in the account</dd></div>
    <div><dt>Matched by Kredibel</dt><dd class="v">89.6%</dd><dd class="n">242 of 270 bank lines</dd><dd class="mini"><i style="width:89.6%"></i></dd></div>
    <div class="is-attn"><dt>Needs you</dt><dd class="v">9</dd><dd class="n">4 possible copies, 5 to match or explain</dd></div>
    <div><dt>Documents</dt><dd class="v">92</dd><dd class="n">1 still reading</dd></div>
  </dl>
</section>"""
    flow_views = seg("flowview", [("flow", "Flow"), ("bars", "Bars"), ("table", "Table"), ("parties", "By client and supplier")], "flow", "Chart type")
    fw_note = ('<p class="chart-note" data-text-group="fw" '
               'data-text-ifrs="IFRS: interest paid (12.0) is a financing cash flow, as IAS 7 classifies it after IFRS 18; applied to 2026 for comparability." '
               'data-text-us_gaap="US GAAP: interest paid (12.0) is an operating cash flow (ASC 230), so operating activities are larger and financing smaller.">'
               'IFRS: interest paid (12.0) is a financing cash flow, as IAS 7 classifies it after IFRS 18; applied to 2026 for comparability.</p>')
    flow = f"""
<article class="chart-panel" aria-labelledby="flow-h">
  <div class="chart-head">
    <div><h3 id="flow-h">Money flow</h3><p>From your clients, through ACB ••4821, to each line of the cash-flow statement. Click a band to list its bank lines.</p></div>
    {flow_views}
  </div>
  <div data-show-group="flowview" data-show-value="flow">
    {tiers(by_fw(charts.statement_sankey), by_fw(lambda fw: charts.statement_sankey(fw, 860)), by_fw(charts.flow_list))}
  </div>
  <div data-show-group="flowview" data-show-value="bars" hidden>{by_fw(charts.spend_bars)}</div>
  <div data-show-group="flowview" data-show-value="table" hidden>{by_fw(charts.flow_table)}</div>
  <div data-show-group="flowview" data-show-value="parties" hidden><div class="chart-roomy">{sankey_svg()}</div><div class="chart-compact">{flow_list()}</div></div>
  <p class="flow-callout">{icon("lightbulb")}<span><strong>Cost of sales took 41.6% of revenue.</strong> Green Valley Farms alone was IDR 318.2 M, paid to the same account every month except one transfer in May (see Risk).</span></p>
  <div class="chart-foot">{fw_note}<a class="link" href="month.html">{icon("list", "icon icon-sm")}See bank lines</a></div>
</article>"""
    monthly = f"""
<article class="chart-panel" aria-labelledby="months-chart-h">
  <div class="chart-head">
    <div><h3 id="months-chart-h">Money in and out by month</h3><p>Net above each pair. March is the month with the edited statement.</p></div>
    {seg("monthview", [("inout", "In and out"), ("net", "Net and balance")], "inout", "Chart type")}
  </div>
  <div data-show-group="monthview" data-show-value="inout">
    {tiers(charts.monthly_bars(), charts.monthly_bars(medium=True), charts.monthly_bars(compact=True))}
    <p class="chart-legend"><span class="in"><i></i>Money in</span><span class="out"><i></i>Money out</span></p>
  </div>
  <div data-show-group="monthview" data-show-value="net" hidden>
    {tiers(charts.net_bars(), charts.net_bars(medium=True), charts.net_bars(compact=True))}
    <p class="chart-legend"><span class="net"><i></i>Net cash flow</span><span class="bal"><i></i>Balance at month end</span></p>
  </div>
</article>"""
    statement = f"""
<article class="chart-panel" aria-labelledby="cfs-h">
  <div class="chart-head">
    <div><h3 id="cfs-h">Cash-flow statement</h3><p>Opening balance to closing balance, by activity. <span data-text-group="fw" data-text-ifrs="IFRS (IAS 7)." data-text-us_gaap="US GAAP (ASC 230).">IFRS (IAS 7).</span></p></div>
    <a class="link" href="month.html">{icon("table", "icon icon-sm")}By month</a>
  </div>
  {tiers(by_fw(charts.waterfall), by_fw(lambda fw: charts.waterfall(fw, medium=True)), by_fw(lambda fw: charts.waterfall(fw, compact=True)))}
</article>"""
    charts_section = f"""
<section class="charts" aria-labelledby="charts-h">
  <div class="section-head charts-section-head">
    <div><h2 class="type-h2" id="charts-h">Where the money went</h2><p>January to June 2026, IDR millions, grouped the way your accounting framework groups cash flows.</p></div>
    <div class="fw-switch"><span>Framework</span>{seg("fw", [("IFRS", "IFRS"), ("US_GAAP", "US GAAP")], "IFRS", "Accounting framework")}</div>
  </div>
  {flow}
  {monthly}
  {statement}
</section>"""
    lists = f"""
<div class="dash-lists">
  <section class="panel" aria-labelledby="todo-h">
    <div class="panel-head"><h2 id="todo-h">Needs you</h2><a class="link" href="review.html">All 9</a></div>
    {todo_list()}
  </section>
  <section class="panel" aria-labelledby="risk-h">
    <div class="panel-head"><h2 id="risk-h">Risk</h2><a class="link" href="risk.html">All findings</a></div>
    <ul class="alert-list">
      <li><a href="evidence-viewer.html"><span class="sev">{sev_badge("critical")}</span><span><p class="a-t">March statement edited after the bank issued it</p><p class="a-s">Balance breaks on 14 Mar; a later revision in a PDF editor</p></span></a></li>
      <li><a href="risk.html"><span class="sev">{sev_badge("high")}</span><span><p class="a-t">Roastline Equipment Service paid to a new account</p><p class="a-s">6 May, IDR 24,500,000 to Meridian Savings ••7720; before: ACB ••3381</p></span></a></li>
      <li><a href="risk.html"><span class="sev">{sev_badge("medium")}</span><span><p class="a-t">Invoices from an unknown supplier</p><p class="a-s">Bluewater Trading Co., 2 invoices, never paid, not in the ledger</p></span></a></li>
    </ul>
  </section>
</div>"""
    found = f"""
<section class="found" aria-label="Profile suggestions">
  {icon("sparkles", "icon icon-lg")}
  <p><strong>Kredibel found 2 details for your profile:</strong> your tax ID and your address, both printed on your sales invoices. Nothing changes until you accept.</p>
  <a class="button button-secondary" href="plan-usage.html">Review details</a>
</section>"""
    months = f"""
<section aria-labelledby="months-h">
  <div class="section-head"><h2 class="type-h2" id="months-h">Months</h2><a class="link" href="month.html">Reconciliation</a></div>
  {month_tabs()}
</section>"""
    content = f"""
<div class="page">
  <div class="dash">
    {hero}
    {figs}
    {lists}
    {charts_section}
    {months}
    {found}
  </div>
</div>"""
    period = f'<span class="period hide-compact">{icon("calendar")}Jan to Jun 2026{icon("chevron-down")}</span>'
    top = topbar("Dashboard", ("Dashboard",), extra=period)
    return shell("dashboard", top, content)


# ------------------------------------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------------------------------------

def documents() -> str:
    tray = f"""
<section class="tray" aria-labelledby="tray-h">
  <div class="tray-drop">
    <span class="ico">{icon("upload")}</span>
    <p><strong id="tray-h">Drop statements, invoices, receipts or a ledger export</strong>PDF, photos, CSV or Excel, in any order. A file you already sent is never read twice.</p>
    <a class="button button-primary" href="#">{icon("plus", "icon icon-sm")}Choose files</a>
    <a class="button button-secondary only-compact" href="#">{icon("camera", "icon icon-sm")}Photo of a receipt</a>
  </div>
  <ul class="tray-list" aria-label="Just uploaded">
    <li><span class="file-ico is-dup">{icon("copy")}</span><span class="f">ACB_Feb_2026 (1).pdf</span><span class="m is-dup">Already uploaded on 2 Jul as <a href="labels.html">ACB_Feb_2026.pdf</a>. Not read again and not counted.</span></li>
    <li><span class="file-ico is-held">{icon("copy")}</span><span class="f">Receipt 0617 (2).jpg</span><span class="m">Looks like <a href="review.html">Receipt 0617.jpg</a> (same merchant, date and total). Held until you decide.</span><span class="act"><a class="button button-secondary button-sm" href="review.html">Decide</a></span></li>
    <li><span class="file-ico is-busy">{icon("refresh")}</span><span class="f">ACB_Jun_2026.pdf</span><span class="m">Reading page 2 of 3<span class="pbar"><i style="width:58%"></i></span></span></li>
    <li><span class="file-ico">{icon("table")}</span><span class="f">ledger-2026-H1.csv</span><span class="m">New column layout. Check the columns once and every row is imported.</span><span class="act"><a class="button button-primary button-sm" href="review.html">Check columns</a></span></li>
  </ul>
</section>"""
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
# Month (reconciliation of March)
# ------------------------------------------------------------------------------------------------

def month() -> str:
    # Categories are badges coloured by cash-flow class (operating, investing, financing, not cash,
    # not categorized); support is a chip per state (ADR-025), so different states never look alike.
    lines = [
        ("10 Mar", "VAT PAYMENT FEB", "−4,860,000", "out", ("Tax", "brand"), ("auto", "link", "Ledger entry, 10 Mar"), "Same amount and date in the ledger", False),
        ("11 Mar", "TRANSFER IN DAYBREAK CAFE", "+6,420,000", "in", ("Sales receipts", "brand"), ("auto", "link", "Invoice 0007"), "Same amount, same client, paid 5 days after issue", False),
        ("12 Mar", "TRANSFER OUT GREEN VALLEY FARMS 0912", "−9,850,000", "out", ("Purchases for sale or production", "brand"), ("proposed", "eye", "Proposed: invoice GVF-2026-0311"), "Same amount and supplier; check it before it counts", False),
        ("12 Mar", "TRANSFER TO OWN SAVINGS ••7710", "−2,000,000", "out", ("Between own accounts", "outline"), ("excluded", "refresh", "Not counted"), "Between your own accounts, so not money in or out", False),
        ("14 Mar", "TRANSFER IN HARBORVIEW HOTEL GROUP", "+7,250,000", "in", ("Sales receipts", "brand"), ("none", "unlink", "No match"), "Your ledger and invoice 0009 say IDR 1,250,000", True),
        ("15 Mar", "TRANSFER OUT PRIMEPACK PACKAGING", "−3,180,000", "out", ("Other suppliers and services", "brand"), ("manual", "hand", "Invoice PP/26/0312"), "Matched by Maya on 12 Jul", False),
        ("16 Mar", "MONTHLY ACCOUNT FEE", "−35,000", "out", ("Bank fees", "brand"), ("cleared", "check", "No document needed"), "Maya: the bank's own fee, no invoice", False),
        ("17 Mar", "PURCHASE ESPRESSO MACHINE", "−18,400,000", "out", ("Equipment bought", "low"), ("none", "file-text", "No document yet"), "Bank cash is recorded; upload its invoice", False),
        ("18 Mar", "DEBIT CARD CENDANA FUEL STATION", "−650,000", "out", ("Not categorized yet", "medium"), ("auto", "link", "Receipt, 18 Mar"), "Same amount, merchant and date", False),
    ]
    trs = []
    for d, desc, amt, direction, (cat, cat_cls), (mk, mi, ml), reason, flagged in lines:
        amt_cls = "amt-in" if direction == "in" else "amt-out"
        amt_html = f'<span class="reading reading-agreed">{amt}</span>'
        ev = f' <a class="citation" href="evidence-viewer.html">{icon("eye")}Evidence</a>' if flagged else ""
        trs.append(f"""<tr{' class="is-flagged"' if flagged else ''}>
  <td data-cell="wide"><strong>{desc}</strong><div class="reason">{d}</div><span class="badge badge-{cat_cls}">{cat}</span></td>
  <td class="r"><span class="{amt_cls}">{amt_html}</span></td>
  <td data-cell="wide"><span class="match-chip {mk}">{icon(mi)}<span>{ml}</span></span><div class="reason">{reason}{ev}</div></td>
</tr>""")
    table = f"""
<div class="table-panel rt-wrap">
  <table class="data-table rt">
    <thead><tr><th>Bank line</th><th class="r">Amount, IDR</th><th>Matched with</th></tr></thead>
    <tbody>{''.join(trs)}</tbody>
  </table>
</div>"""
    explain = f"""
<section class="explain" aria-labelledby="ex-h">
  <h2 class="explain-head" id="ex-h">{icon("octagon-alert")}Critical: the March statement was edited after the bank issued it</h2>
  <div class="explain-body">
    <p class="lead">On 14 March the statement shows a credit of IDR 7,250,000 from Harborview Hotel Group <a class="citation" href="evidence-viewer.html">{icon("eye")}A01</a>, but the printed balance rises by only IDR 1,250,000. The file was saved again in a PDF editor three days after the bank created it <a class="citation" href="#">{icon("eye")}M03</a>, and that one amount is set in a different font <a class="citation" href="#">{icon("eye")}M04</a>. Your ledger records IDR 1,250,000 for the same payment <a class="citation" href="#">{icon("table")}Ledger, 14 Mar</a>.</p>
    <div class="stack gap-2">
      <h3 class="type-h3">What to do next</h3>
      <ol class="steps">
        <li>Download the March statement again from internet banking and upload it.</li>
        <li>If the bank's copy shows IDR 1,250,000, ask who sent you this file before you close March.</li>
        <li>Keep March open until then; Kredibel will compare the two statements for you.</li>
      </ol>
    </div>
    <span class="by-line">{icon("sparkles")}Written by Gemini. Every figure checked by Kredibel.</span>
  </div>
</section>"""
    content = f"""
<div class="page">
  <div class="month-head">
    <div class="row">
      <span class="month-switch"><a href="#" aria-label="February">{icon("chevron-left")}</a><a href="#" aria-label="April">{icon("chevron-right")}</a></span>
      <h1 class="type-title">March 2026</h1>
      <span class="badge badge-status badge-medium">2 need you</span>{sev_badge("critical")}
    </div>
    <p class="muted">ACB ••4821. Statement, 9 invoices, 4 receipts and 52 ledger entries for this month.</p>
  </div>
  <div class="stack gap-6" style="margin-top:24px">
    <section class="ledger" aria-label="March figures">
      <dl class="ledger-figures">
        <div><dt>Opening balance</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">47.9 M</span></dd><dd class="n">Same as February's closing</dd></div>
        <div><dt>Money in</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">231.4 M</span></dd><dd class="n">21 credits</dd></div>
        <div><dt>Money out</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">218.9 M</span></dd><dd class="n">24 debits</dd></div>
        <div><dt>Closing balance</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">60.4 M</span></dd><dd class="n">As printed</dd></div>
        <div><dt>Matched by Kredibel</dt><dd class="v">86%</dd><dd class="n">39 of 45 bank lines</dd><dd class="mini"><i style="width:86%"></i></dd></div>
        <div class="is-attn"><dt>Ledger difference</dt><dd class="v"><small>IDR</small>6.0 M</dd><dd class="n">Bank shows more than the ledger</dd></div>
      </dl>
    </section>
    {explain}
    <section class="recon-meter" aria-label="Bank lines by match state">
      <div class="bar"><i class="auto" style="width:86.7%"></i><i class="manual" style="width:11.1%"></i><i class="open" style="width:2.2%"></i></div>
      <p class="key"><span><i class="auto"></i>Matched by Kredibel <b>39</b></span><span><i class="manual"></i>Matched by you <b>5</b></span><span><i class="open"></i>Open <b>1</b></span></p>
    </section>
    <div class="stack gap-3">
      <nav class="tabs" role="tablist" aria-label="March sections"><a class="tab" role="tab" aria-selected="true" href="#">Bank lines <span class="count">45</span></a><a class="tab" role="tab" aria-selected="false" href="#">Documents <span class="count">14</span></a><a class="tab" role="tab" aria-selected="false" href="#">Ledger <span class="count is-attn">1 difference</span></a><a class="tab" role="tab" aria-selected="false" href="#">Findings <span class="count">6</span></a></nav>
      <div class="chips" role="group" aria-label="Filter bank lines"><a class="chip" aria-pressed="true" href="#">All <span class="n">45</span></a><a class="chip" href="#">Open <span class="n">1</span></a><a class="chip" href="#">Money in <span class="n">21</span></a><a class="chip" href="#">Money out <span class="n">24</span></a></div>
      {table}
      <p class="reading-legend"><span><span class="reading reading-agreed">7,250,000</span> both readings agree</span><span><span class="reading reading-single">7,250,000</span> one reading only</span><span><span class="reading reading-conflict">7,250,000</span> readings disagree</span></p>
    </div>
  </div>
</div>"""
    return shell("months", topbar("March 2026", (("Reconciliation", "month.html"), "March 2026"), back=("Dashboard", "dashboard.html")), content)


# ------------------------------------------------------------------------------------------------
# Review queue
# ------------------------------------------------------------------------------------------------

def review() -> str:
    groups = [
        ("February", [("dup", "copy", "Possible copy of the February statement", "Same account and period, 45 identical lines", False),
                      ("match", "link", "IDR 18,700,000 on 9 Feb fits two invoices", "Daybreak Café, invoices 0003 and 0004", True)]),
        ("March", [("match", "link", "IDR 7,250,000 on 14 Mar differs from your ledger", "Harborview Hotel Group; ledger and invoice 0009 say IDR 1,250,000", False),
                   ("dup", "copy", "Possible copy of invoice GVF-2026-0311", "Scanned again; same supplier, number and total", False)]),
        ("May", [("dup", "copy", "Ledger line entered twice", "12 May, IDR 4,350,000", False),
                 ("doc", "file-text", "Invoice BLU-2026-118 never paid", "Bluewater Trading Co., IDR 31,800,000", False),
                 ("doc", "file-text", "Invoice BLU-2026-121 never paid", "Bluewater Trading Co., IDR 27,450,000", False)]),
        ("June", [("dup", "copy", "Receipt photographed twice", "Cendana Fuel Station, 17 Jun, IDR 820,000", False),
                  ("doc", "wallet", "Cash deposit not in the ledger", "21 Jun, IDR 2,150,000", False)]),
    ]
    q = []
    for g, items in groups:
        q.append(f'<li class="queue-group"><span>{g}</span><span>{len(items)}</span></li>')
        for k, ic, t, s, cur in items:
            c = ' aria-current="true"' if cur else ""
            q.append(f'<li><a class="qitem" href="review.html"{c}><span class="kind {k}">{icon(ic)}</span><span class="t">{t}</span><span class="s">{s}</span></a></li>')
    queue = f"""
<section class="panel hide-compact" aria-label="Review queue" style="overflow:hidden">
  <div class="panel-head"><h2>9 open</h2><span class="muted small">Oldest month first</span></div>
  <ul class="queue todo-list">{''.join(q)}</ul>
</section>"""
    chips = "".join(
        f'<a class="chip" href="#"{" aria-pressed=\"true\"" if i == 0 else ""}>{label} <span class="n">{n}</span></a>'
        for i, (label, n) in enumerate([("All", 9), ("Possible copies", 4), ("Choose a match", 1), ("Explain a difference", 1), ("Not paid", 2), ("Not in the ledger", 1)]))
    def why(ok, text):
        return f'<span class="why-tag {"yes" if ok else "no"}">{icon("check" if ok else "x")}{text}</span>'
    fix = f"""
<section class="fix" aria-labelledby="fix-h">
  <div class="fix-head">
    <div class="pager-line"><span class="row"><span class="badge badge-brand">{icon("link")}Choose a match</span><span>February</span></span><span class="only-compact">2 of 9</span></div>
    <h2 id="fix-h">IDR 18,700,000 on 9 Feb fits two invoices</h2>
    <p>Both invoices are from Daybreak Café for the same amount. Kredibel only matches on its own when one answer is clearly better, so this one is yours.</p>
  </div>
  <div class="fix-body">
    <div class="subject"><span class="ico">{icon("bank")}</span><span class="t">TRANSFER IN DAYBREAK CAFE</span><span class="amt amt-in">+18,700,000</span><span class="s">9 Feb, ACB ••4821, statement page 1 <a class="citation" href="#">{icon("eye")}See on the page</a></span></div>
    <div class="candidates" role="radiogroup" aria-label="Invoices that fit">
      <div class="candidate is-picked" role="radio" aria-checked="true" tabindex="0" data-label="Match with invoice 0003"><span class="radio"></span><span><span class="t">Invoice INV/SCR/2026/02/0003</span><br/><span class="s">Issued 2 Feb, due 16 Feb</span></span><span class="amt">18,700,000</span>
        <span class="why">{why(True, "Same amount")}{why(True, "Same client")}{why(True, "Paid 7 days after issue")}{why(False, "No invoice number in the transfer")}</span>
        <span class="score">Fit<span class="meter-bar"><i style="width:78%"></i></span>0.78</span></div>
      <div class="candidate" role="radio" aria-checked="false" tabindex="-1" data-label="Match with invoice 0004"><span class="radio"></span><span><span class="t">Invoice INV/SCR/2026/02/0004</span><br/><span class="s">Issued 6 Feb, due 6 Mar</span></span><span class="amt">18,700,000</span>
        <span class="why">{why(True, "Same amount")}{why(True, "Same client")}{why(True, "Paid 3 days after issue")}{why(False, "No invoice number in the transfer")}</span>
        <span class="score">Fit<span class="meter-bar"><i style="width:76%"></i></span>0.76</span></div>
    </div>
    <p class="flow-callout" style="margin:0">{icon("lightbulb")}<span>Invoice 0003 was due first, and Daybreak's next payment on 4 Mar fits invoice 0004 by date.</span></p>
    <div class="other-actions"><a class="button button-quiet button-sm" href="#">Match something else</a><a class="button button-quiet button-sm" href="#">Neither invoice</a></div>
  </div>
  <div class="fix-foot">
    <a class="button button-primary" href="review.html" data-picked-label>{icon("check", "icon icon-sm")}<span>Match with invoice 0003</span></a>
    <a class="button button-secondary hide-compact" href="#">Skip</a>
    <span class="keys"><span><span class="kbd">J</span> <span class="kbd">K</span> next, previous</span><span><span class="kbd">Enter</span> match</span></span>
  </div>
</section>"""
    content = f"""
<div class="page review">
  <div class="page-head">
    <h1 class="type-title">Review</h1>
    <p>What Kredibel could not settle on its own. Each fix is saved with your name and the month is reconciled again.</p>
  </div>
  <div class="stack gap-4">
    <div class="chips" role="group" aria-label="Filter by kind">{chips}</div>
    <div class="review-layout">{queue}{fix}</div>
  </div>
</div>"""
    return shell("review", topbar("Review", ("Review",)), content, fab=False)


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
# Document (one read statement: the viewer beside what was read)
# ------------------------------------------------------------------------------------------------

def document() -> str:
    # ACB_Feb_2026.pdf: February as in the other mocks (money in 214.9 M, out 208.1 M, 45 lines,
    # closing 47.9 M = March's opening), page 1 of 3, with 9 Feb's Daybreak Café credit selected.
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
    list_rows = [
        ("3 Feb", "TRANSFER OUT GREEN VALLEY FARMS 0912", "−12,400,000.00", "out", "agreed"),
        ("4 Feb", "CASH DEPOSIT", "+2,050,000.00", "in", "agreed"),
        ("5 Feb", "TRANSFER IN SPICE ROUTE RESTAURANT", "+9,800,000.00", "in", "agreed"),
        ("6 Feb", "DEBIT CARD CENDANA FUEL STATION", "−720,000.00", "out", "single"),
        ("9 Feb", "TRANSFER IN DAYBREAK CAFE", "+18,700,000.00", "in", "agreed"),
        ("10 Feb", "VAT PAYMENT JAN", "−4,410,000.00", "out", "agreed"),
        ("11 Feb", "TRANSFER OUT PRIMEPACK PACKAGING", "−3,060,000.00", "out", "agreed"),
        ("12 Feb", "INSTANT TRANSFER IN HIGHLAND RESORT &amp; SPA", "+7,600,000.00", "in", "agreed"),
        ("13 Feb", "TRANSFER OUT ANDI PRATAMA", "−5,000,000.00", "out", "agreed"),
    ]
    trs = "".join(
        f"""<tr class="is-clickable{' is-selected' if desc.endswith('DAYBREAK CAFE') else ''}"{' aria-selected="true"' if desc.endswith('DAYBREAK CAFE') else ''}>
  <td><strong>{desc}</strong><div class="reason">{day}, page 1</div></td>
  <td class="r"><span class="{'amt-in' if way == 'in' else 'amt-out'}"><span class="reading reading-{mark}">{amt}</span></span></td>
</tr>""" for day, desc, amt, way, mark in list_rows)
    page = statement_page(page_rows, "01 Feb 2026 to 28 Feb 2026", "Page 1 / 3",
                          "February statement, page 1, with the selected credit highlighted")
    viewer = f"""
<section class="viewer" aria-label="Page viewer">
  <div class="viewer-bar">
    <span class="file">{icon("file-text", "icon icon-sm")}ACB_Feb_2026.pdf</span>
    <span class="pages" role="group" aria-label="Pages"><button type="button" aria-label="Previous page" disabled>{icon("chevron-left", "icon icon-sm")}</button><span>Page 1 of 3</span><button type="button" aria-label="Next page">{icon("chevron-right", "icon icon-sm")}</button></span>
    <span class="zoom" role="group" aria-label="Zoom"><button type="button" aria-label="Zoom out">{icon("zoom-out", "icon icon-sm")}</button><span>100%</span><button type="button" aria-label="Zoom in">{icon("zoom-in", "icon icon-sm")}</button></span>
  </div>
  <div class="doc-window">{page}</div>
  <div class="spread"><p class="muted small">The box shows where the selected value is printed, from the word positions in the file itself.</p><button class="button button-secondary button-sm whole-page" type="button">{icon("file-text", "icon icon-sm")}Whole page</button></div>
</section>"""
    pane = f"""
<section class="doc-pane" aria-label="What was read">
  <dl class="ledger-figures">
    <div><dt>Opening balance</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">41.1 M</span></dd><dd class="n">1 Feb, as printed</dd></div>
    <div><dt>Closing balance</dt><dd class="v"><small>IDR</small><span class="reading reading-agreed">47.9 M</span></dd><dd class="n">28 Feb, as printed</dd></div>
    <div><dt>Money in</dt><dd class="v"><small>IDR</small>214.9 M</dd><dd class="n">21 credits</dd></div>
    <div><dt>Money out</dt><dd class="v"><small>IDR</small>208.1 M</dd><dd class="n">24 debits</dd></div>
  </dl>
  <nav class="tabs" role="tablist" aria-label="Document sections"><a class="tab" role="tab" aria-selected="true" href="#">Transactions <span class="count">45</span></a><a class="tab" role="tab" aria-selected="false" href="#">Findings <span class="count">0</span></a><a class="tab" role="tab" aria-selected="false" href="#">Details</a></nav>
  <div class="chips" role="group" aria-label="Filter transactions"><a class="chip" aria-pressed="true" href="#">All <span class="n">45</span></a><a class="chip" href="#">Money in <span class="n">21</span></a><a class="chip" href="#">Money out <span class="n">24</span></a><a class="chip" href="#">To check <span class="n">1</span></a></div>
  <div class="table-panel rt-wrap"><table class="data-table rt">
    <thead><tr><th>Transaction</th><th class="r">Amount, IDR</th></tr></thead>
    <tbody>{trs}</tbody>
  </table></div>
  <div class="pager-line"><span>1 to 10 of 45</span><span class="row"><button class="button button-secondary button-sm" type="button" disabled>Previous</button><button class="button button-secondary button-sm" type="button">Next</button></span></div>
  <p class="reading-legend"><span><span class="reading reading-agreed">18,700,000</span> found on the page</span><span><span class="reading reading-single">720,000</span> read from the image only</span><span><span class="reading reading-conflict">7,250,000</span> page and reading differ</span></p>
</section>"""
    content = f"""
<div class="page stack gap-5">
  <header class="stack gap-2">
    <h1 class="type-title">ACB_Feb_2026.pdf</h1>
    <p class="muted">Bank statement, Archipelago Commerce Bank ••4821, 1 to 28 February 2026. Uploaded on 2 July.</p>
    <div class="doc-status">
      <span class="badge badge-brand">{icon("check")}Read: 180 of 180 values found on the page</span>
      <span class="badge badge-clean">{icon("shield-check")}No signs of editing</span>
      <span class="spacer"></span>
      <span class="row"><a class="button button-secondary button-sm" href="#">{icon("download", "icon icon-sm")}Original file</a><a class="button button-ghost button-sm" href="#">{icon("trash", "icon icon-sm")}Remove</a></span>
    </div>
  </header>
  <div class="doc-layout">{viewer}{pane}</div>
</div>"""
    return shell("documents", topbar("ACB_Feb_2026.pdf", (("Documents", "documents.html"), "ACB_Feb_2026.pdf"), back=("Documents", "documents.html")), content)


# ------------------------------------------------------------------------------------------------
# Finance Assistant (P1)
# ------------------------------------------------------------------------------------------------

def assistant() -> str:
    content = f"""
<div class="page">
  <div class="page-head">
    <div class="spread"><h1 class="type-title">Assistant</h1><span class="badge badge-outline">Preview</span></div>
    <p>Ask about your books. Numbers come from your reconciled data, never from memory, and every answer shows its source.</p>
  </div>
  <div class="chat-layout">
    <div class="stack gap-5">
      <div class="chat">
        <p class="msg-user">How much did we pay Green Valley Farms in March?</p>
        <div class="msg-ai"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="Kredibel"/>
          <div class="bubble">
            <p>You paid Green Valley Farms <strong>IDR 56,050,000</strong> in March, in 3 transfers <a class="citation" href="month.html">{icon("table")}3 bank lines</a>. All three went to their usual account, ACB ••0912, and each one matches an invoice.</p>
            <div class="mini-bars" role="img" aria-label="Three transfers: 5 Mar 32.1 million, 12 Mar 9.85 million, 26 Mar 14.1 million">
              <div class="mb"><span>5 Mar</span><span class="bar" style="width:100%"></span><b>32.10 M</b></div>
              <div class="mb"><span>12 Mar</span><span class="bar" style="width:31%"></span><b>9.85 M</b></div>
              <div class="mb"><span>26 Mar</span><span class="bar" style="width:44%"></span><b>14.10 M</b></div>
            </div>
            <span class="grounded">{icon("shield-check")}Every number checked against your books</span>
          </div>
        </div>
        <p class="msg-user">Why is March critical?</p>
        <div class="msg-ai"><img class="ai-mark" src="{BRAND}/kredibel-mark.svg" alt="Kredibel"/>
          <div class="bubble">
            <p>Because the March statement looks edited <a class="citation" href="evidence-viewer.html">{icon("eye")}A01</a>. On 14 March it shows IDR 7,250,000 from Harborview Hotel Group, but the balance only rises by IDR 1,250,000, and your ledger and invoice 0009 also say 1,250,000.</p>
            <p>The quickest check is to download March again from internet banking and upload it. Want me to open the evidence?</p>
            <div class="row"><a class="button button-secondary button-sm" href="evidence-viewer.html">Open the evidence</a><a class="button button-quiet button-sm" href="month.html">Go to March</a></div>
          </div>
        </div>
      </div>
      <div class="suggested" aria-label="Suggested questions"><a href="#">Which invoices are still unpaid?</a><a href="#">Where did the money go in Q2?</a><a href="#">Who are my biggest clients?</a></div>
      <div class="composer"><p>Ask about your books</p><button class="button button-primary" type="button" aria-label="Send">{icon("send", "icon icon-sm")}</button></div>
    </div>
    <aside class="chat-aside stack gap-4">
      <section class="panel panel-pad stack gap-3" aria-labelledby="mem-h">
        <div class="spread"><h2 class="type-h3" id="mem-h">Remembered for you</h2><a class="link small" href="#">Forget all</a></div>
        <ul class="remembered"><li><span>Show amounts in millions</span><a class="link small" href="#">Forget</a></li><li><span>ACB ••5577 is the payroll account</span><a class="link small" href="#">Forget</a></li><li><span>The financial year starts in January</span><a class="link small" href="#">Forget</a></li></ul>
        <p class="muted small">Only preferences are remembered. Figures are always read fresh from your books.</p>
      </section>
      <section class="panel panel-pad stack gap-2" aria-labelledby="thr-h">
        <h2 class="type-h3" id="thr-h">Earlier questions</h2>
        <a class="link" href="#">Unpaid invoices in May</a><a class="link" href="#">Payroll this year</a>
      </section>
    </aside>
  </div>
</div>"""
    return shell("assistant", topbar("Assistant", ("Assistant",)), content, fab=False)


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
        plan("Free trial", "Free for 30 days", ["Every feature of the prototype", "Up to 3 team members", "400 pages read per month"], True),
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


# ------------------------------------------------------------------------------------------------
# Onboarding
# ------------------------------------------------------------------------------------------------

def onboarding() -> str:
    brand = f"""
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
    form = f"""
<section class="onboard-form" aria-labelledby="ob-h">
  <div class="stack gap-2"><h1 class="type-title" id="ob-h">Set up your business</h1><p class="muted">One workspace is one business. You can add details later; Kredibel will suggest them from your documents.</p></div>
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


SCREENS = {
    "dashboard": ("Dashboard", dashboard),
    "documents": ("Documents", documents),
    "document": ("Document", document),
    "month": ("Month reconciliation", month),
    "reconciliation": ("Bank evidence and document support", reconciliation),
    "review": ("Review queue", review),
    "evidence-viewer": ("Evidence viewer", evidence_viewer),
    "assistant": ("Finance Assistant", assistant),
    "plan-usage": ("Plan and usage", plan_usage),
    "onboarding": ("Onboarding", onboarding),
}

NOTES = {
    "dashboard": "One sentence says where the books stand, then what needs you and the open risks. Below, full-width charts grouped by IFRS or US GAAP: money flow (flow, bars, table or by client and supplier), money in and out by month, and the cash-flow statement.",
    "document": "One read document: the page viewer with the selected value lit, beside what was read from it, a paginated list with reading marks, its findings and details.",
    "documents": "Upload anything in any order. Exact copies are recognised at once; possible copies wait for you; ledgers ask for their columns once.",
    "month": "One month's reconciliation: figures with their provenance marks, the explained risk with next steps, and every bank line with its match and reason.",
    "reconciliation": "A separate synthetic MYR workspace preview: grouped and split payments, bank-only rows, documents before statements, separate approval/payment confirmation and currency agreement without conversion.",
    "review": "One queue for everything AI could not settle. Each item shows the evidence, the candidates and only the fixes that make sense.",
    "evidence-viewer": "The lamp on the printed value, the calculation, and both readings side by side. Phones open zoomed to the evidence.",
    "assistant": "Questions about your books, answered from tools with citations and a small chart; only preferences are remembered.",
    "plan-usage": "Trial days, usage that warns before a limit, coming-soon plans and features that cannot be clicked.",
    "onboarding": "Individual or company in one question; the brand panel explains the promise with a ledger.",
}
