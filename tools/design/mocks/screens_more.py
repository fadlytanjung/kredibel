"""More screens: Risk, Clients and suppliers, Labels (spec 016) and Runs (spec 017).
Same demo workspace as screens.py; counts agree with the dashboard and the review queue."""

from __future__ import annotations

from icons import icon
from screens import month_tabs, seg, sev_badge
from shell import shell, topbar

# ------------------------------------------------------------------------------------------------
# Risk
# ------------------------------------------------------------------------------------------------

FINDINGS = [
    ("March", "critical", [
        ("critical", "A01", "Running balance does not add up on 14 Mar", "ACB_Mar_2026.pdf, page 2", "Open"),
        ("high", "M04", "One amount is drawn in a different font from its column", "ACB_Mar_2026.pdf, page 2", "Open"),
        ("high", "M03", "Saved again in a PDF editor three days after the bank created it", "ACB_Mar_2026.pdf", "Open"),
        ("high", "X09", "Bank shows IDR 6,000,000 more than the ledger", "March, ledger-2026-H1.csv", "Open"),
        ("medium", "D03", "Invoice GVF-2026-0311 scanned again", "GVF-2026-0311 (scan).pdf", "Held"),
        ("low", "E05", "Buyer name on one receipt is unclear", "Receipt 0318.jpg", "Open"),
    ]),
    ("May", "high", [
        ("high", "X08", "Roastline Equipment Service paid to a new account", "6 May, IDR 24,500,000 to Meridian Savings ••7720", "Open"),
        ("medium", "R02", "Invoice BLU-2026-118 from a supplier never seen in the bank", "BLU-2026-118.pdf", "Open"),
        ("medium", "R02", "Invoice BLU-2026-121 from a supplier never seen in the bank", "BLU-2026-121.pdf", "Open"),
        ("medium", "D06", "Ledger line entered twice", "12 May, IDR 4,350,000", "Held"),
    ]),
    ("February", "medium", [
        ("medium", "D02", "Statement period overlaps an earlier upload", "ACB_Feb_2026 (re-download).pdf", "Held"),
    ]),
    ("June", "medium", [
        ("medium", "D05", "Receipt photographed twice", "Receipt 0617 (2).jpg", "Held"),
    ]),
]


def risk() -> str:
    groups = []
    for month, level, rows in FINDINGS:
        trs = "".join(
            f'<tr{" class=\"is-flagged\"" if sev == "critical" else ""}><td><a class="find-link" href="evidence-viewer.html">{sev_badge(sev)}<span class="code-tag">{code}</span><span class="find-t">{title}</span></a><span class="sub">{where}</span></td>'
            f'<td class="hide-rt">{where}</td><td class="r"><span class="status-line {"wait" if st == "Held" or sev == "medium" else "bad" if sev in ("critical", "high") else ""}">{st}</span></td></tr>'
            for sev, code, title, where, st in rows)
        groups.append(f"""
<section class="find-group" aria-label="{month}">
  <div class="find-head"><h2 class="type-h3">{month} 2026</h2>{sev_badge(level)}<a class="link" href="month.html">Open {month}</a></div>
  <div class="table-panel rt-wrap"><table class="data-table rt find-table">
    <thead><tr><th>Finding</th><th class="hide-rt">Where</th><th class="r">Status</th></tr></thead>
    <tbody>{trs}</tbody></table></div>
</section>""")
    chips = "".join(f'<a class="chip" href="risk.html"{" aria-pressed=\"true\"" if i == 0 else ""}>{t} <span class="n">{n}</span></a>'
                    for i, (t, n) in enumerate([("All", 12), ("Critical", 1), ("High", 4), ("Medium", 6), ("Low", 1), ("Held copies", 4)]))
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">Risk</h1>
    <p><strong>2 months need attention.</strong> March is critical because its statement was edited; May is high because a supplier was paid to a new account. Every finding opens on the page it came from.</p>
  </div>
  <div class="stack gap-6">
    <section aria-label="Risk by month">{month_tabs()}</section>
    <div class="chips" role="group" aria-label="Filter by severity">{chips}</div>
    {''.join(groups)}
    <p class="muted small">January and April have no open findings. Dismissed findings stay in the audit trail.</p>
  </div>
</div>"""
    return shell("risk", topbar("Risk", ("Risk",)), content)


# ------------------------------------------------------------------------------------------------
# Clients and suppliers
# ------------------------------------------------------------------------------------------------

PARTIES = [
    ("Harborview Hotel Group", "building", "Client", "in", 412.5, 30.4, 18, "1 account", ""),
    ("Highland Resort & Spa", "building", "Client", "in", 318.0, 23.5, 12, "1 account", ""),
    ("Daybreak Café", "building", "Client", "in", 196.4, 14.5, 24, "1 account", ""),
    ("Spice Route Restaurant", "building", "Client", "in", 154.8, 11.4, 11, "1 account", ""),
    ("Hillside Coffee Bar", "building", "Client", "in", 121.6, 9.0, 12, "1 account", ""),
    ("Green Valley Farms", "building", "Supplier", "out", 318.2, 24.7, 7, "1 account", ""),
    ("PrimePack Packaging", "building", "Supplier", "out", 142.3, 11.1, 6, "1 account", ""),
    ("Roastline Equipment Service", "building", "Supplier", "out", 48.5, 3.8, 2, "2 accounts", "New account in May (X08)"),
    ("Bluewater Trading Co.", "building", "Supplier", "out", 0.0, 0.0, 0, "none", "2 invoices, never paid (R02)"),
    ("Archipelago Commerce Bank", "bank", "Lender", "out", 60.0, 4.7, 6, "loan account", ""),
    ("Maya Sari", "user", "Owner", "out", 72.0, 5.6, 6, "1 account", ""),
]


def clients() -> str:
    trs = []
    for name, ic, role, d, v, share, n, acc, flag in PARTIES:
        amt = f'<span class="{"amt-in" if d == "in" else "amt-out"}">{"+" if d == "in" else "−"}{v:,.1f}</span>' if v else '<span class="muted">0.0</span>'
        flag_html = f'<span class="badge badge-high">{icon("triangle-alert")}{flag}</span>' if "X08" in flag else (f'<span class="badge badge-medium">{icon("circle-alert")}{flag}</span>' if flag else "")
        trs.append(f"""<tr{" class=\"is-flagged\"" if "X08" in flag else ""}>
  <td><span class="doc-cell"><span class="thumb">{icon(ic)}</span><span><strong>{name}</strong><span class="sub">{role}</span></span></span></td>
  <td class="r">{amt}</td>
  <td class="hide-rt"><span class="share"><span class="meter-bar"><i style="width:{share * 3:.0f}%"></i></span><span>{share:.1f}%</span></span></td>
  <td class="r hide-rt">{n}</td>
  <td data-cell="wide">{acc} {flag_html}</td>
</tr>""")
    chips = "".join(f'<a class="chip" href="clients.html"{" aria-pressed=\"true\"" if i == 0 else ""}>{t} <span class="n">{n}</span></a>'
                    for i, (t, n) in enumerate([("All", 11), ("Clients", 5), ("Suppliers", 4), ("Lenders", 1), ("Owner", 1)]))
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">Clients and suppliers</h1>
    <p>Who your money comes from and goes to, built from the bank lines, invoices and receipts. A supplier paid to an account not seen before is flagged.</p>
  </div>
  <div class="stack gap-3">
    <div class="chips" role="group" aria-label="Filter by role">{chips}</div>
    <div class="table-panel rt-wrap"><table class="data-table rt">
      <thead><tr><th>Name</th><th class="r">IDR M, Jan to Jun</th><th class="hide-rt">Share of money in or out</th><th class="r hide-rt">Transfers</th><th>Accounts seen</th></tr></thead>
      <tbody>{''.join(trs)}</tbody></table></div>
    <p class="muted small">Roles come from invoices, categories and matches. Correct a role on the Labels page.</p>
  </div>
</div>"""
    return shell("clients", topbar("Clients and suppliers", ("Clients and suppliers",)), content)


# ------------------------------------------------------------------------------------------------
# Labels (spec 016)
# ------------------------------------------------------------------------------------------------

PAGES = {
    "ACB_Mar_2026.pdf": [("p1", "Summary", 0.99, "ACB_Mar_2026-p2.md"), ("p2", "Transactions", 0.98, "ACB_Mar_2026-p2.md"), ("p3", "Terms or cover", 0.62, "ACB_Mar_2026-p3.md")],
    "Receipt 0617.jpg": [("p1", "Receipt", 0.71, "Receipt-0617-p1.md")],
    "RES-0045.pdf": [("p1", "Invoice", 0.98, "RES-0045-p1.md")],
    "BLU-2026-118.pdf": [("p1", "Invoice", 0.95, "BLU-2026-118-p1.md")],
    "INV-SCR-2026-06-0024.pdf": [("p1", "Invoice", 0.97, "INV-SCR-2026-06-0024-p1.md")],
}


def page_chips(subject: str) -> str:
    doc = subject.split(",")[0]
    pages = PAGES.get(doc)
    if not pages:
        return ""
    chips = "".join(
        f'<a class="pchip {"lo" if c < 0.7 else "mid" if c < 0.9 else "hi"}" href="samples/{f}" title="Page type {t}, confidence {c:.2f}">{n} {t} <b>{c:.2f}</b></a>'
        for n, t, c, f in pages)
    return f'<span class="page-chips" aria-label="Per-page types">{chips}</span>'


# subject, sub, task, ai value, confidence, status, decided, source, extraction (file, page label), run, dataset, selected
LABELS = [
    ("TRANSFER OUT ROASTLINE EQUIPMENT", "6 May, −24,500,000, ACB_May_2026.pdf p1", "Category", "Repairs and services", 0.66, "needs", "", "Flash-Lite, categorize v4", ("ACB_May_2026-p1.md", "p1.md"), "run …8M", "Excluded", True),
    ("ACB_Mar_2026.pdf, page 3", "Statement, 3 pages", "Page type", "Terms or cover", 0.62, "needs", "", "Flash, read_page v3", ("ACB_Mar_2026-p3.md", "p3.md"), "run …7K", "Excluded", False),
    ("CASH DEPOSIT", "21 Jun, +2,150,000, ACB_Jun_2026.pdf p2", "Category", "Sales receipts", 0.58, "needs", "", "Flash-Lite, categorize v4", ("ACB_Jun_2026-p2.md", "p2.md"), "run …9C", "Excluded", False),
    ("INV-SCR-2026-06-0024.pdf", "Sales invoice, total", "Value", "4,200,000.00", None, "needs", "", "One reading only", ("INV-SCR-2026-06-0024-p1.md", "p1.md"), "run …9D", "Excluded", False),
    ("Receipt 0617.jpg, page 1", "Photo", "Page type", "Receipt", 0.71, "needs", "", "Flash, read_page v3", ("Receipt-0617-p1.md", "p1.md"), "run …9A", "Excluded", False),
    ("TRANSFER OUT GREEN VALLEY FARMS 0912", "12 Mar, −9,850,000, ACB_Mar_2026.pdf p2", "Category", "Purchases (cost of sales)", 0.81, "corrected", "Maya, 12 Jul. Was: Other suppliers. Rule: similar lines", "Person", ("ACB_Mar_2026-p2.md", "p2.md"), "run …7K", "Train", False),
    ("DEBIT INTEREST LOAN", "25 Mar, −2,000,000, ACB_Mar_2026.pdf p3", "Category", "Interest paid (financing, IFRS)", 0.74, "verified", "Maya, 12 Jul", "Flash-Lite, categorize v4", ("ACB_Mar_2026-p3.md", "p3.md"), "run …7K", "Eval", False),
    ("ACB_Mar_2026.pdf, page 2", "Statement, 3 pages", "Page type", "Statement transactions", 0.98, "verified", "Maya, 12 Jul", "Flash, read_page v3", ("ACB_Mar_2026-p2.md", "p2.md"), "run …7K", "Train", False),
    ("ledger-2026-H1.csv", "Ledger export, 1,184 rows", "Document type", "Ledger export", 0.99, "verified", "Maya, 2 Jul", "Flash-Lite, classify v2", None, "run …6Z", "Train", False),
    ("RES-0045.pdf", "Purchase invoice, Roastline Equipment Service", "Document type", "Purchase invoice", 0.97, "proposed", "", "Code: buyer is this workspace", ("RES-0045-p1.md", "p1.md"), "run …8L", "Excluded", False),
    ("BLU-2026-118.pdf, page 1", "Purchase invoice", "Page type", "Invoice", 0.95, "proposed", "", "Flash, read_page v3", ("BLU-2026-118-p1.md", "p1.md"), "run …8N", "Excluded", False),
    ("Hillside Coffee Bar", "Counterparty", "Counterparty role", "Client", 0.97, "proposed", "", "Code: buyer on 12 sales invoices", None, "run …9F", "Excluded", False),
]
STATUS = {
    "needs": ('<span class="lbl-status needs">' + "Needs a check" + "</span>"),
    "proposed": '<span class="lbl-status proposed">AI proposed</span>',
    "verified": '<span class="lbl-status verified">{ic}Verified by a person</span>',
    "corrected": '<span class="lbl-status corrected">{ic}Corrected by a person</span>',
}


def conf(v: float | None) -> str:
    if v is None:
        return '<span class="conf none">no score</span>'
    lvl = "lo" if v < 0.7 else "mid" if v < 0.9 else "hi"
    return f'<span class="conf {lvl}"><span class="conf-bar"><i style="width:{v * 100:.0f}%"></i></span><span>{v:.2f}</span></span>'


def labels() -> str:
    trs = []
    for subj, sub, task, val, c, st, dec, src, ext, run, ds, sel in LABELS:
        status = STATUS[st].replace("{ic}", icon("check", "icon icon-sm"))
        ext_html = f'<a class="md-link" href="samples/{ext[0]}">{icon("markdown", "icon icon-sm")}{ext[1]}</a>' if ext else '<span class="muted">none</span>'
        dec_html = f'<span class="sub">{dec}</span>' if dec else ""
        trs.append(f"""<tr data-row{" class=\"is-selected\"" if sel else ""}>
  <td class="chk hide-rt"><input type="checkbox" aria-label="Select {subj}"{" checked" if st == "needs" and sel else ""}/></td>
  <td data-cell="wide"><span class="lbl-subj"><strong>{subj}</strong><span class="sub">{sub}</span>{page_chips(subj)}</span></td>
  <td data-cell="wide"><span class="task">{task}</span><span class="lbl-val">{val}</span>{dec_html}</td>
  <td>{conf(c)}</td>
  <td>{status}</td>
  <td class="hide-rt small muted">{src}</td>
  <td class="hide-rt">{ext_html}</td>
  <td class="hide-rt"><a class="run-link" href="runs.html">{run}</a></td>
  <td class="hide-rt"><span class="ds {ds.lower()}">{ds}</span></td>
</tr>""")
    tasks = seg("task", [("all", "All 1,284"), ("doc", "Document type 92"), ("page", "Page type 214"), ("cat", "Category 812"), ("role", "Role 14"), ("value", "Value 152")], "all", "Task")
    status = "".join(f'<a class="chip" href="labels.html"{" aria-pressed=\"true\"" if i == 0 else ""}>{t} <span class="n">{n}</span></a>'
                     for i, (t, n) in enumerate([("Needs a check", 37), ("AI proposed", 1035), ("Verified", 201), ("Corrected", 11)]))
    md = """# ACB_May_2026.pdf, page 1 of 3
Page type: STATEMENT_TRANSACTIONS (0.97)
Reading: AI_TEXT_LAYER, agreement 0.99

| Row | Date  | Description                      | Debit         | Balance       | Readings |
|-----|-------|----------------------------------|---------------|---------------|----------|
| 6   | 06/05 | TRANSFER OUT ROASTLINE EQUIPMENT | 24,500,000.00 | 31,940,000.00 | agreed   |
|     |       | to MERIDIAN SAVINGS ••7720       |               |               |          |"""
    panel = f"""
<aside class="lbl-panel panel" aria-labelledby="lp-h">
  <div class="lp-main">
  <div class="lp-head"><span class="task">Category</span><span class="lbl-status needs">Needs a check</span></div>
  <h2 id="lp-h" class="type-h3">TRANSFER OUT ROASTLINE EQUIPMENT</h2>
  <p class="muted small">6 May 2026, −IDR 24,500,000, ACB ••4821. Counterparty: Roastline Equipment Service.</p>
  <div class="lp-ai">
    <div><span class="k">AI proposed</span><strong>Repairs and services</strong><span class="sub">Operating expenses, operating activity (IFRS)</span></div>
    {conf(0.66)}
  </div>
  <p class="lp-why">{icon("sparkles", "icon icon-sm")}<span>Looks like equipment maintenance; the matching invoice RES-0045 says "service visit and parts". Confidence is low because this payment went to a new account.</span></p>
  <div class="field"><label for="lp-cat">Category</label>
    <select class="select" id="lp-cat"><option>Repairs and services (Operating expenses)</option><option>Equipment bought (Investing)</option><option>Purchases for sale or production (Cost of sales)</option><option>Other spending</option></select></div>
  <label class="check-row"><input type="checkbox" checked/> Apply to similar lines from Roastline Equipment Service</label>
  <div class="field"><label for="lp-note">Note <span class="muted">(optional)</span></label><input class="input" id="lp-note" placeholder="Why, for whoever checks next"/></div>
  <div class="row lp-actions"><a class="button button-primary" href="labels.html">{icon("check", "icon icon-sm")}Confirm</a><a class="button button-secondary" href="labels.html">Save correction</a></div>
  </div>
  <div class="lp-side">
  <details class="lp-md" open><summary>{icon("markdown", "icon icon-sm")}Extraction, ACB_May_2026.pdf page 1</summary><pre>{md}</pre><a class="link small" href="samples/ACB_May_2026-p1.md">Open p1.md</a></details>
  <dl class="lp-prov">
    <div><dt>Model</dt><dd>Gemini Flash-Lite</dd></div>
    <div><dt>Prompt</dt><dd>categorize v4, 5 verified examples</dd></div>
    <div><dt>Run</dt><dd><a href="runs.html">run_01JB8M…</a>, span 7c2e</dd></div>
    <div><dt>Dataset</dt><dd>Excluded until a person decides</dd></div>
  </dl>
  </div>
</aside>"""
    content = f"""
<div class="page">
  <div class="page-head">
    <div class="spread"><h1 class="type-title">Labels</h1><span class="badge badge-outline">Preview</span></div>
    <p><strong>212 of 1,284 labels checked by people; the AI was right on 94.8% of them.</strong> 37 need a check. A label a person confirms or corrects is verified by a person and is never overwritten by a later run.</p>
  </div>
  <div class="stack gap-3">
    <div class="spread lbl-tools">{tasks}<span class="fw-pill">{icon("book", "icon icon-sm")}Categories follow IFRS. <a href="plan-usage.html">Change</a></span></div>
    <div class="chips" role="group" aria-label="Filter by status">{status}</div>
    <div class="bulk-bar"><span><strong>1 selected</strong></span><a class="button button-secondary button-sm" href="labels.html">{icon("check", "icon icon-sm")}Confirm as proposed</a><span class="muted small">Corrections are one at a time.</span></div>
    <div class="lbl-layout">
      <div class="table-panel rt-wrap"><table class="data-table rt lbl-table">
        <thead><tr><th class="chk hide-rt"><span class="sr-only">Select</span></th><th>Subject and per-page types</th><th>Label</th><th>Confidence</th><th>Status</th><th class="hide-rt">Source</th><th class="hide-rt">Extraction</th><th class="hide-rt">Run</th><th class="hide-rt">Dataset</th></tr></thead>
        <tbody>{''.join(trs)}</tbody></table></div>
      {panel}
    </div>
    <div class="spread lbl-foot"><p class="muted small">Showing 12 of 1,284, lowest confidence first. Training consent is off: verified labels are used only as examples and evals inside this workspace.</p>
      <button class="button button-secondary button-sm" type="button" disabled>{icon("download", "icon icon-sm")}Export dataset (later)</button></div>
  </div>
</div>"""
    return shell("labels", topbar("Labels", ("Labels",)), content)


# per-page classifier strip for the docs page of each document (used in the samples index)
SAMPLES = {
    "ACB_Mar_2026-p2.md": """# ACB_Mar_2026.pdf, page 2 of 3
Page type: STATEMENT_TRANSACTIONS (0.98, Gemini Flash, read_page v3)
Reading: AI_TEXT_LAYER, agreement 0.97
SYNTHETIC, FOR TESTING

| Row | Date  | Description                           | Debit        | Credit       | Balance       | Readings |
|-----|-------|---------------------------------------|--------------|--------------|---------------|----------|
| 12  | 10/03 | VAT PAYMENT FEB                       | 4,860,000.00 |              | 38,940,000.00 | agreed   |
| 13  | 11/03 | TRANSFER IN DAYBREAK CAFE             |              | 6,420,000.00 | 45,360,000.00 | agreed   |
| 14  | 12/03 | TRANSFER OUT GREEN VALLEY FARMS 0912  | 9,850,000.00 |              | 35,510,000.00 | agreed   |
| 15  | 12/03 | CASH DEPOSIT                          |              | 2,240,000.00 | 37,750,000.00 | agreed   |
| 16  | 13/03 | TRANSFER IN SPICE ROUTE RESTAURANT    |              | 3,500,000.00 | 41,250,000.00 | agreed   |
| 17  | 14/03 | TRANSFER IN HARBORVIEW HOTEL GROUP    |              | 7,250,000.00 | 42,500,000.00 | agreed   |
| 18  | 15/03 | TRANSFER OUT PRIMEPACK PACKAGING      | 3,180,000.00 |              | 39,320,000.00 | agreed   |

## Checks on this page
| Code | Result |
|------|--------|
| A01  | Row 17: 41,250,000.00 + 7,250,000.00 = 48,500,000.00, printed 42,500,000.00 |
| M04  | Row 17 credit drawn in Helvetica; the column uses DejaVu Sans |
""",
    "ACB_Mar_2026-p3.md": """# ACB_Mar_2026.pdf, page 3 of 3
Page type: TERMS_OR_COVER (0.62, Gemini Flash, read_page v3), needs a check
Reading: AI_TEXT_LAYER, agreement 1.00
SYNTHETIC, FOR TESTING

| Row | Date  | Description          | Debit        | Credit | Balance       | Readings |
|-----|-------|----------------------|--------------|--------|---------------|----------|
| 31  | 25/03 | DEBIT INTEREST LOAN  | 2,000,000.00 |        | 58,410,000.00 | agreed   |
| 32  | 31/03 | ADMIN FEE            | 15,000.00    |        | 58,395,000.00 | agreed   |

Most of this page is the bank's terms and contact details; two rows were read.
""",
}
for _name in ["ACB_May_2026-p1.md", "ACB_Jun_2026-p2.md", "INV-SCR-2026-06-0024-p1.md", "Receipt-0617-p1.md", "RES-0045-p1.md", "BLU-2026-118-p1.md"]:
    SAMPLES.setdefault(_name, f"# {_name.replace('-p', ', page ').replace('.md', '')}\nSYNTHETIC, FOR TESTING\n\nSample extraction file for the mocks. The real file lists the page type with its confidence,\nthe reading method, the witness text, line items as a table and both readings of every value\n(docs/07-document-intelligence.md §8).\n")


# ------------------------------------------------------------------------------------------------
# Runs (spec 017)
# ------------------------------------------------------------------------------------------------

RUNS = [
    ("files", "Document", "ACB_Mar_2026.pdf", "ok", "Done", "2 Jul, 09:14", "41.2 s", 5, "18.4k / 3.1k", "0.021", "Flash, Flash-Lite", "4 proposed, 2 verified", True),
    ("reconcile", "Month", "2026-03, generation 7", "ok", "Done", "12 Jul, 10:02", "6.8 s", 1, "4.2k / 0.6k", "0.004", "Flash", "45 proposed, 1 corrected", False),
    ("reconcile", "Month", "2026-03, generation 6", "wait", "Superseded", "12 Jul, 10:01", "2.1 s", 0, "none", "0.000", "none", "none", False),
    ("sparkles", "Assistant", "Why is March critical?", "ok", "Done", "12 Jul, 10:20", "3.9 s", 2, "6.1k / 0.4k", "0.003", "Flash", "none", False),
    ("table", "Document", "ledger-2026-H1.csv", "ok", "Done", "2 Jul, 09:11", "4.4 s", 2, "1.9k / 0.3k", "0.001", "Flash-Lite", "1 proposed, 1 verified", False),
    ("files", "Document", "ACB_Jun_2026.pdf", "busy", "Reading page 2 of 3", "Today, 10:31", "18.0 s", 2, "7.0k / 1.2k", "0.008", "Flash", "2 proposed", False),
    ("files", "Document", "Receipt 0617 (2).jpg", "wait", "Held as a possible copy", "10 Jul, 16:40", "7.2 s", 2, "3.3k / 0.4k", "0.003", "Flash, OCR", "2 proposed", False),
]
# name, depth, start s, end s, kind, detail
SPANS = [
    ("workflow:document_workflow", 0, 0.0, 41.2, "wf", "ACB_Mar_2026.pdf, 3 pages"),
    ("node:inspect", 1, 0.2, 1.1, "code", "pikepdf, 2 revisions"),
    ("node:classify", 1, 1.1, 3.0, "llm", "Flash-Lite, 2.1k in, 0.1k out: BANK_STATEMENT 0.99"),
    ("node:read_pages", 1, 3.0, 36.8, "node", "page 1 first, then 2 and 3 in parallel"),
    ("read_page p1", 2, 3.0, 12.4, "llm", "Flash, 3.4k in, 0.9k out: STATEMENT_SUMMARY 0.99"),
    ("witness p1 to p3 (text layer)", 2, 3.0, 3.6, "code", "1,204 words with boxes"),
    ("read_page p2", 2, 12.5, 24.9, "llm", "Flash, 3.6k in, 1.4k out: STATEMENT_TRANSACTIONS 0.98"),
    ("read_page p3", 2, 12.5, 19.1, "llm sel", "Flash, 3.3k in, 0.3k out: TERMS_OR_COVER 0.62"),
    ("node:verify", 1, 36.8, 37.9, "code", "agreement 0.97, 0 conflicts"),
    ("node:duplicates", 1, 37.9, 38.2, "code", "no copy"),
    ("node:forensics", 1, 38.2, 39.6, "code", "A01, M03, M04"),
    ("node:categorize", 1, 39.6, 41.0, "llm", "Flash-Lite, 45 CATEGORY labels"),
]


def runs() -> str:
    trs = []
    for ic, kind, target, st, stl, when, dur, calls, tok, usd, models, lbls, sel in RUNS:
        trs.append(f"""<tr data-row{" class=\"is-selected\"" if sel else ""}>
  <td data-cell="wide"><span class="doc-cell"><span class="thumb">{icon(ic)}</span><span><strong>{target}</strong><span class="sub">{kind} run</span></span></span></td>
  <td><span class="status-line {st}">{stl}</span></td>
  <td class="hide-rt">{when}</td>
  <td class="r">{dur}</td>
  <td class="r hide-rt">{calls}</td>
  <td class="r hide-rt">{tok}</td>
  <td class="r hide-rt">{usd}</td>
  <td class="hide-rt small">{models}</td>
  <td class="hide-rt small">{lbls}</td>
</tr>""")
    T = 41.2
    rows = []
    for name, depth, a, b, kind, detail in SPANS:
        left, width = a / T * 100, max((b - a) / T * 100, 0.6)
        rows.append(f"""<li class="span-row d{depth} {kind}">
  <span class="span-name">{name}</span>
  <span class="span-track"><i style="left:{left:.2f}%;width:{width:.2f}%"></i></span>
  <span class="span-dur">{b - a:.1f} s</span>
  <span class="span-detail">{detail}</span>
</li>""")
    axis = "".join(f'<span style="left:{t / T * 100:.1f}%">{t} s</span>' for t in (0, 10, 20, 30, 40))
    chips = "".join(f'<a class="chip" href="runs.html"{" aria-pressed=\"true\"" if i == 0 else ""}>{t} <span class="n">{n}</span></a>'
                    for i, (t, n) in enumerate([("All", 214), ("Document", 182), ("Month", 26), ("Assistant", 6), ("Failed", 0), ("Corrected by a person", 9)]))
    inspector = f"""
<aside class="ev-inspector panel" aria-labelledby="ev-h">
  <div class="lp-main">
  <div class="lp-head"><span class="task">LLM call</span><span class="lbl-status needs">Label needs a check</span></div>
  <h2 id="ev-h" class="type-h3">read_page p3</h2>
  <dl class="lp-prov">
    <div><dt>Model</dt><dd>Gemini Flash</dd></div>
    <div><dt>Prompt</dt><dd>read_page v3</dd></div>
    <div><dt>Latency</dt><dd>6.6 s</dd></div>
    <div><dt>Tokens</dt><dd>3,312 in, 286 out</dd></div>
    <div><dt>Span</dt><dd>9f41 in trace 4be0…</dd></div>
  </dl>
  <div class="row"><a class="button button-secondary button-sm" href="labels.html">{icon("tag", "icon icon-sm")}Open the label</a><a class="button button-quiet button-sm" href="#" data-external>{icon("external", "icon icon-sm")}Cloud Trace</a><a class="button button-quiet button-sm" href="#" data-external>{icon("table", "icon icon-sm")}BigQuery rows</a></div>
  </div>
  <div class="lp-side">
  <details open><summary>Request</summary><pre>system: read_page v3 (values as printed, no arithmetic)
input: page image ACB_Mar_2026.pdf p3 (1,120 tokens)
context: account ••4821, period 01–31 Mar 2026</pre></details>
  <details open><summary>Response</summary><pre>{{"page_type": "TERMS_OR_COVER",
 "page_type_confidence": 0.62,
 "rows": [{{"row_on_page": 0, "date_text": "25/03",
   "description": "DEBIT INTEREST LOAN", "debit_text": "2,000,000.00"}}, …]}}</pre></details>
  <p class="muted small">Content is captured because this workspace holds synthetic data (AI_CONTENT_CAPTURE=synthetic). Account numbers are masked.</p>
  </div>
</aside>"""
    content = f"""
<div class="page">
  <div class="page-head">
    <div class="spread"><h1 class="type-title">Runs</h1><span class="badge badge-outline">Owner only</span></div>
    <p>Every document, month and assistant run, call by call: what ran, how long it took, what it cost, and what people corrected afterwards. Traces live in Cloud Trace; every call is a row in BigQuery.</p>
  </div>
  <div class="stack gap-5">
    <div class="chips" role="group" aria-label="Filter runs">{chips}</div>
    <div class="table-panel rt-wrap"><table class="data-table rt runs-table">
      <thead><tr><th>Run</th><th>Status</th><th class="hide-rt">Started</th><th class="r">Duration</th><th class="r hide-rt">LLM calls</th><th class="r hide-rt">Tokens in / out</th><th class="r hide-rt">USD</th><th class="hide-rt">Models</th><th class="hide-rt">Labels</th></tr></thead>
      <tbody>{''.join(trs)}</tbody></table></div>
    <section class="run-detail" aria-labelledby="rd-h">
      <div class="spread"><div><h2 class="type-h2" id="rd-h">document_workflow on ACB_Mar_2026.pdf</h2><p class="muted small">2 Jul 2026, 09:14. 41.2 s, 5 LLM calls, 18.4k tokens in, 3.1k out, about USD 0.021. Prompts: classify v2, read_page v3, categorize v4.</p></div>
        <span class="row"><a class="link" href="evidence-viewer.html">Findings A01, M03, M04</a></span></div>
      <div class="run-layout">
        <div class="panel waterfall-panel">
          <div class="span-axis" aria-hidden="true"><span class="span-name"></span><span class="span-track">{axis}</span></div>
          <ol class="spans">{''.join(rows)}</ol>
          <p class="span-legend"><span class="llm"><i></i>Model call</span><span class="code"><i></i>Code</span><span class="node"><i></i>Workflow and nodes</span></p>
        </div>
        {inspector}
      </div>
    </section>
  </div>
</div>"""
    return shell("runs", topbar("Runs", ("Runs",)), content, fab=False)


def landing() -> str:
    """The public landing mock (spec 020): ink hero, the two readings, one live decision, the story."""
    brand = "../brand"
    shots = "../../docs/assets/mocks"
    nav = "".join(
        f'<a href="dashboard.html">{label}</a>'
        for label in ("How it works", "Security", "Pricing", "FAQ", "Contact")
    )
    rows = "".join(
        [
            '<div class="statement-row"><span class="d">05 Mar</span>'
            '<span class="desc">TRANSFER OUT GREEN VALLEY FARMS</span>'
            '<span class="amt reading reading-agreed">32,100,000</span></div>',
            '<div class="statement-row"><span class="d">11 Mar</span>'
            '<span class="desc">TRANSFER IN DAYBREAK CAFE</span>'
            '<span class="amt reading reading-agreed">6,420,000</span></div>',
            '<div class="statement-row is-held"><span class="d">12 Mar</span>'
            '<span class="desc">ACB_Feb_2026 (1).pdf</span><span class="amt">Held</span></div>',
        ]
    )
    steps = "".join(
        f'<div class="how-row"><div><h3>{title}</h3><p>{body}</p></div></div>'
        for title, body in [
            ("Duplicates first", "An exact copy is recorded and never read again; a re-exported statement is held until you decide."),
            ("Read twice, pay once", "Gemini reads every page image; the text layer, or Document AI OCR for scans, is the witness."),
            ("Ledger files by code", "The AI proposes the columns once; you confirm; code imports every row."),
            ("Forensics", "Running balances, PDF revisions, odd fonts and statement continuity, on every document."),
            ("Months that reconcile themselves", "Exact, split and net-of-tax matches with reasons, in any upload order."),
            ("A short, honest review queue", "The ~15% AI could not match, with the evidence and the right fixes."),
            ("Fraud risk you can explain", "A policy file sets the level; Gemini explains it and orders the next steps."),
        ]
    )
    return f"""<div class="viewport"><div class="site">
  <header class="site-header is-dark">
    <a class="site-lockup" href="dashboard.html" aria-label="Kredibel home"><img src="{brand}/kredibel-logo-on-dark.svg" alt="Kredibel"/></a>
    <nav class="site-nav" aria-label="Menu">{nav}</nav>
    <div class="site-actions">
      <a class="button button-inverse hide-compact" href="onboarding.html">Sign in</a>
      <a class="button button-primary" href="onboarding.html">Start free trial</a>
      <button type="button" class="icon-button site-menu-button" aria-label="Open menu">{icon("menu")}</button>
    </div>
  </header>
  <main class="site-main">
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <p class="hero-eyebrow">{icon("sparkles", "icon icon-sm")}AI finance workspace</p>
          <h1 class="hero-title">Every number has a source.</h1>
          <p class="hero-lead">Kredibel reads every page twice and checks your books — duplicates, edited documents and unmatched payments, caught before they count.</p>
          <div class="hero-actions">
            <a class="button button-primary button-lg" href="onboarding.html">Start free trial</a>
            <a class="button button-inverse button-lg" href="dashboard.html">See how it works</a>
          </div>
          <p class="hero-trust">
            <span>{icon("check", "icon icon-sm")}Built on Google Cloud</span>
            <span>{icon("check", "icon icon-sm")}No card, no payment</span>
            <span>{icon("check", "icon icon-sm")}Reads documents in any language</span>
          </p>
        </div>
        <div class="hero-visual">
        <div class="statement-sheet">
          <div class="statement-head"><span class="bank"><i aria-hidden="true"></i>ACB ••4821</span><span class="meta">Statement,<br/>March 2026</span></div>
          <div class="read-twice" data-state="settled">
            <span class="rt-mark ai">{icon("ai-reader", "icon icon-sm")}AI reader</span>
            <span class="rt-value reading reading-agreed">32,100,000</span>
            <span class="rt-mark wit">{icon("text-layer", "icon icon-sm")}Witness</span>
          </div>
          <p class="read-twice-caption">read twice — the value is trusted only when both readings agree</p>
          <div class="statement-rows">{rows}</div>
          <div class="statement-foot"><span>Closing balance</span><span class="total">18,703,918</span></div>
        </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-inner">
        <div class="section-head"><p class="eyebrow">Why Kredibel</p><h2>Books closed by hand, weeks after the fact.</h2>
        <p>Three things go wrong before anyone notices — and by then they have already been counted.</p></div>
        <div class="problem-grid">
          <div class="problem-card"><h3>What goes wrong</h3><ul class="problem-list">
            <li>{icon("circle-alert", "icon icon-sm icon-bad")}<span>The same statement is uploaded twice, or a supplier invoice is scanned again, and an expense is counted twice.</span></li>
            <li>{icon("circle-alert", "icon icon-sm icon-bad")}<span>A PDF can be edited in minutes, and a supplier's account can be a fraudster's.</span></li>
            <li>{icon("circle-alert", "icon icon-sm icon-bad")}<span>A payment to a new account sits in the books until someone spots it, if at all.</span></li>
          </ul></div>
          <div class="problem-card is-solution"><h3>What Kredibel does instead</h3><ul class="problem-list">
            <li>{icon("check", "icon icon-sm icon-good")}<span>An exact copy is recorded and never read again; a possible copy is held until you decide.</span></li>
            <li>{icon("check", "icon icon-sm icon-good")}<span>Every number is read twice and counted only when both readings agree.</span></li>
            <li>{icon("check", "icon icon-sm icon-good")}<span>Each month reconciles itself, and the few things AI cannot settle wait in one short review queue.</span></li>
          </ul></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-inner">
        <div class="split">
          <div class="stack gap-6">
            <div class="section-head"><p class="eyebrow">How it works</p><h2>Upload anything, in any order.</h2>
            <p>The upload order never changes the result.</p></div>
            <div class="how-list">{steps}</div>
          </div>
          <div class="split-visual">
            <figure class="shot"><img src="{shots}/month-desktop.png" alt="" loading="lazy"/><figcaption>One month, reconciled.</figcaption></figure>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-inner">
        <div class="section-head"><p class="eyebrow">Fraud risk</p><h2>Fraud risk you can explain.</h2>
        <p>Deterministic checks find the problem; Gemini explains it and orders what to do next.</p></div>
        <div class="hero-inner">
          <div class="explain">
            <div class="explain-head">{icon("octagon-alert", "icon icon-sm")}Critical</div>
            <div class="explain-body">
              <h3 class="type-h1"><span class="code-tag">A01</span> Running balance does not add up on 14 Mar</h3>
              <p class="lead">The statement shows <span class="lamp">86,420,000</span>, then 124,520,000 after an amount of 32,100,000 — the balance moves by 6,000,000 more than the amounts printed.</p>
              <div class="calc"><table><tbody>
                <tr><td class="op"></td><td>Balance before</td><td class="amt">86,420,000</td></tr>
                <tr><td class="op">+</td><td>Amount on the page</td><td class="amt">32,100,000</td></tr>
                <tr class="total"><td class="op"></td><td>Balance that should follow</td><td class="amt">118,520,000</td></tr>
                <tr class="diff"><td class="op"></td><td>Balance printed</td><td class="amt">124,520,000</td></tr>
              </tbody></table></div>
            </div>
          </div>
          <figure class="shot"><img src="{shots}/evidence-viewer-desktop.png" alt="" loading="lazy"/><figcaption>See the evidence</figcaption></figure>
        </div>
      </div>
    </section>

    <section class="section is-ink">
      <div class="section-inner">
        <div class="section-head"><p class="eyebrow">Built to be trusted</p><h2>Your books stay yours.</h2>
        <p>The rules that keep the product honest are in the product.</p></div>
        <ul class="ticks">
          <li>{icon("shield-check", "icon icon-sm")}<span>Documents are data, never instructions; quarantined files never reach a model</span></li>
          <li>{icon("shield-check", "icon icon-sm")}<span>Two independent readings before any accusation; disagreement is uncertainty, not fraud</span></li>
          <li>{icon("shield-check", "icon icon-sm")}<span>Every finding, match and figure carries its evidence and its reason</span></li>
          <li>{icon("shield-check", "icon icon-sm")}<span>A person resolves the exceptions; nothing is confirmed or deleted silently</span></li>
        </ul>
        <div class="hero-actions">
          <a class="button button-primary button-lg" href="onboarding.html">Start free trial</a>
          <a class="button button-inverse button-lg" href="dashboard.html">How it works</a>
        </div>
      </div>
    </section>
  </main>
  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="brand-blurb"><img src="{brand}/kredibel-logo-on-dark.svg" alt="Kredibel"/>
      <p>Every number has a source. Kredibel is an AI finance workspace that checks a small business's own books.</p></div>
      <div><h3>Product</h3><ul><li><a href="dashboard.html">How it works</a></li><li><a href="dashboard.html">Pricing</a></li><li><a href="dashboard.html">Security</a></li></ul></div>
      <div><h3>Company</h3><ul><li><a href="onboarding.html">Sign in</a></li><li><a href="onboarding.html">Start free trial</a></li></ul></div>
      <div><h3>Legal</h3><ul><li><a href="dashboard.html">Privacy Policy</a></li><li><a href="dashboard.html">Terms of Service</a></li></ul></div>
    </div>
    <div class="foot-bottom"><span>© 2026 Kredibel. It never moves money and never changes your accounting system.</span><span>Demo data is synthetic.</span></div>
  </footer>
</div></div>"""


SCREENS_MORE = {
    "risk": ("Risk", risk),
    "clients": ("Clients and suppliers", clients),
    "labels": ("Labels", labels),
    "runs": ("Runs", runs),
    "landing": ("Landing", landing),
}
NOTES_MORE = {
    "risk": "Findings grouped by month with their severity and status; each opens the evidence viewer.",
    "clients": "Clients and suppliers built from the books; a supplier paid to a new account is flagged.",
    "labels": "Every AI decision a person can check, lowest confidence first, with per-page types, extraction files, runs and dataset use.",
    "runs": "Run history like a tracing tool: runs, a span waterfall, and the selected model call with its request, response and label.",
    "landing": "The public landing page: the two readings converge on one printed figure, then one live duplicate decision, then the story.",
}
