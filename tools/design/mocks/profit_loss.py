"""P&L mocks use the same synthetic report as React stories and visual tests."""
import json
from decimal import Decimal
from html import escape
from pathlib import Path

from icons import icon
from shell import shell, topbar
from sankey import band

ROOT = Path(__file__).resolve().parents[3]
REPORT = json.loads((ROOT / 'contracts/design/fixtures/profit-loss.json').read_text())
WORDS = json.loads((ROOT / 'frontend/src/shared/i18n/locales/en/profitLoss.json').read_text())


def amount(value):
    return f'IDR\u00a0{Decimal(value):,.0f}'


def toggle(group, options, active, label):
    buttons = ''.join(f'<button type="button" data-group="{group}" data-value="{key}" aria-pressed="{str(key == active).lower()}">{word}</button>' for key, word in options)
    return f'<div class="seg" role="group" aria-label="{label}">{buttons}</div>'


def rows():
    maximum = max(abs(Decimal(line['amount'])) for line in REPORT['lines'])
    return ''.join(f'<a class="pnl-row pnl-source-button" href="profit-loss-entries.html"><span>{WORDS["lines"][line["id"]]}</span><strong class="num">{amount(line["amount"])}</strong><span class="pnl-track" aria-hidden="true"><span class="pnl-bar" style="width:{abs(Decimal(line["amount"])) / maximum * 100:.2f}%"></span></span></a>' for line in REPORT['lines'])


def flow():
    sources = [('4000 Sales', 120, 'src'), ('Other income', 1, 'src')]
    uses = [('Cost of sales', 72, 'use'), ('Payroll', 18, 'operating'), ('Finance costs', 2, 'operating'), ('Income tax', 3, 'operating'), ('Net profit', 26, 'kept')]
    total, k, gap, top = 121, 194 / 121, 40, 80
    height = total * k + (len(uses) - 1) * gap
    middle_y = top + (height - total * k) / 2
    parts = ['<svg class="chart sankey" viewBox="0 0 1040 500" role="img" aria-label="Profit and loss">', '<text class="col" x="240" y="22" text-anchor="end">Income sources</text>', '<text class="col" x="520" y="22" text-anchor="middle">Total income</text>', '<text class="col" x="794" y="22">Expenses and profit</text>']
    for nodes, side in [(sources, 'left'), (uses, 'right')]:
        y = top + (height - (total*k + (len(nodes)-1)*gap))/2
        center = middle_y
        for name, value, role in nodes:
            h = value*k
            x = 240 if side == 'left' else 780
            path = band(254, y, y+h, 513, center, center+h, role, name) if side == 'left' else band(527, center, center+h, 780, y, y+h, role, name)
            parts.append(f'<a href="profit-loss-entries.html" aria-label="{escape(name)} {amount(str(value*1000000))}">{path}<rect class="node {role}" x="{x}" y="{y}" width="14" height="{h}"/></a>')
            label_x, anchor = (232, 'end') if side == 'left' else (802, 'start')
            parts.append(f'<text x="{label_x}" y="{y+h/2}" text-anchor="{anchor}"><tspan>{escape(name)}</tspan><tspan class="amt" x="{label_x}" dy="18">{value:.1f} M IDR</tspan></text>')
            y += h + gap
            center += h
    parts.append(f'<a href="profit-loss-entries.html"><rect class="node acc" x="513" y="{middle_y}" width="14" height="{total*k}"/></a><text x="520" y="{middle_y-26}" text-anchor="middle">Total income<tspan class="amt" x="520" dy="18">121.0 M IDR</tspan></text></svg>')
    compact_svg = ''.join(parts)
    exact_svg = compact_svg
    for value in {121, *(v for _, v, _ in sources + uses)}:
        exact_svg = exact_svg.replace(f'{value:.1f} M IDR', amount(str(value * 1000000)))
    return f'<div class="pnl-flow-wrapper stack gap-3"><div class="chart-head"><p class="muted small">Revenue and other income, with expenses and net profit. Select a band or row to inspect its ledger entries.</p>{toggle("pnlunits", [("compact", "Compact"), ("exact", "Exact")], "compact", "Amounts")}</div><div class="pnl-flow-wide"><div data-show-group="pnlunits" data-show-value="compact">{compact_svg}</div><div data-show-group="pnlunits" data-show-value="exact" hidden>{exact_svg}</div></div><div class="pnl-flow-compact pnl-bars">{rows()}</div><p class="chart-note">Amounts formatted compactly; click any node or band for itemized rows.</p></div>'


def panel(detail=False, state='populated'):
    link = '' if detail else '<a class="button button-secondary" href="profit-loss.html">Accounts and sources</a>'
    if state == 'loading':
        return '<section class="panel panel-pad" role="status">Loading profit and loss…</section>'
    if state == 'error':
        return '<section class="panel panel-pad stack gap-3" role="alert"><p>Profit and loss could not be loaded. Check the period and try again.</p><a class="button button-secondary" href="profit-loss.html">Try again</a></section>'
    body = '<p role="status">Profit and loss needs posted general-ledger entries and confirmed account classifications. Bank cash movements cannot establish profit.</p>'
    if state != 'empty':
        table = '<table class="table"><thead><tr><th scope="col">P&amp;L line</th><th scope="col" class="num">Amount</th></tr></thead><tbody>' + ''.join(f'<tr><th scope="row">{WORDS["lines"][line["id"]]}</th><td class="num">{amount(line["amount"])}</td></tr>' for line in REPORT['lines']) + '</tbody></table>'
        body = (('<p role="status">This is a partial report. Review excluded entries and ledger gaps before using its totals.</p>' if state == 'partial' else '') + toggle('pnlview', [('flow', 'Flow'), ('chart', 'Bars'), ('table', 'Table')], 'flow', 'Profit and loss view') + f'<div data-show-group="pnlview" data-show-value="flow">{flow()}</div><div class="pnl-bars" data-show-group="pnlview" data-show-value="chart" hidden>{rows()}</div><div class="table-wrap" data-show-group="pnlview" data-show-value="table" hidden>{table}</div>')
        if state == 'partial':
            body += '<ul><li>Unclassified entries: 2</li><li>Some imported journals do not balance.</li></ul>'
    return f'<section class="chart-panel panel-pad stack gap-4" aria-label="Profit and loss"><div class="chart-head"><div><h2 class="type-h2">Profit and loss</h2><p>Accrual management report for 2026-03</p></div>{link}</div><p class="muted">{WORDS["coverage"]}</p>{body}</section>'


def page(state='populated'):
    classification = '<section class="panel panel-pad stack gap-4"><div><h2 class="type-h2">Account classifications</h2><p class="muted small">Confirm how each company account appears in profit and loss. Subledgers group the supporting detail.</p></div>'
    if state == 'empty':
        classification += '<p class="muted">No general-ledger accounts have been imported.</p>'
    else:
        classification += '<div class="table-panel"><table class="data-table pnl-accounts"><thead><tr><th>Account</th><th>P&amp;L line</th><th>Subledger</th><th class="r">Action</th></tr></thead><tbody><tr><td><div class="doc-cell"><div><strong>4000</strong><span class="sub">Sales</span></div></div></td><td><label class="field m-0"><span class="sr-only">P&amp;L line</span><select class="input" aria-label="P&amp;L line"><option>Revenue</option><option>Balance sheet (excluded from profit)</option></select></label></td><td><label class="field m-0"><span class="sr-only">Subledger</span><select class="input" aria-label="Subledger"><option>Receivables</option><option>General journals</option></select></label></td><td class="r"><button class="button button-primary">Confirm classification</button></td></tr></tbody></table></div>'
    classification += '</section>'
    sources = '<section class="panel panel-pad stack gap-4"><h2 class="type-h2">Source entries</h2><p>Subledger families group accounts; they do not certify a control-account reconciliation.</p>'
    for sub in sorted({e['subledger'] for e in REPORT['entries']}):
        sources += f'<div><h3 class="type-h3">{WORDS["subledgers"][sub]}</h3>'
        for e in REPORT['entries']:
            if e['subledger'] == sub:
                sources += f'<a class="pnl-source link" href="document.html">{e["accountCode"]} {e["accountName"]}, 2 Mar 2026, row {e["rowNumber"]}: {amount(e["amount"])}</a>'
        sources += '</div>'
    sources += '</section>'
    content = '<div class="page stack gap-5"><div class="page-head"><h1 class="type-title">Company profit and loss</h1><p>Company account classifications, with the ledger rows behind every total.</p></div><form class="row items-end"><label class="field">Filter month<select class="input"><option>Select a month…</option><option selected>2026-03</option></select></label><label class="field">Period<input class="input" value="2026-03"/></label><button class="button button-secondary" type="button">Apply period</button></form><p class="muted">Use recent, all, a year (2026), quarter (2026-Q1), month (2026-03), or range (2026-01..2026-03).</p>' + panel(True, state) + classification + (sources if state not in ('empty','loading','error') else '') + '</div>'
    return shell('dashboard', topbar('Profit and loss', (('Dashboard', 'dashboard.html'), 'Profit and loss'), back=('Dashboard', 'dashboard.html')), content, fab=False)


def entries():
    source = REPORT['entries'][0]
    drawer = f'<div class="flow-sheet"><a class="scrim" aria-label="Close entries" href="profit-loss.html"></a><section class="sheet" role="dialog" aria-modal="true" aria-labelledby="pnl-sheet-h"><div class="sheet-head"><div><h2 id="pnl-sheet-h">4000 Sales</h2><p>{amount(source["amount"])}</p><p class="muted small">1 contributing entry</p></div><a class="icon-button" aria-label="Close entries" href="profit-loss.html">{icon("x")}</a></div><div class="sheet-body"><a class="line-row" href="document.html"><div><strong>4000 Sales</strong><p class="muted small">Receivables · 2 Mar 2026 · Row 1</p></div><strong class="amt">{amount(source["amount"])}</strong></a></div></section></div>'
    return page() + drawer
