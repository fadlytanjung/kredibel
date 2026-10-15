"""More screens: Risk, Clients and suppliers, Labels (spec 016) and Runs (spec 017).
Same demo workspace as screens.py; counts agree with the dashboard and the review queue."""

from __future__ import annotations

import json
from decimal import Decimal
from html import escape

from icons import icon
from screens import DASH, LOCALES, RISK_WORDS, ROOT, fmt_date, money_code, month_name, month_tabs, seg, sev_badge, words
from shell import shell, topbar

# ------------------------------------------------------------------------------------------------
# Risk
# ------------------------------------------------------------------------------------------------

RISK = json.loads((ROOT / "contracts/design/fixtures/risk.json").read_text(encoding="utf-8"))
SEV_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def and_list(items: list[str]) -> str:
    """'A', 'A and B', 'A, B and C': the page's own join (English UI)."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def finding_where(f: dict, files: dict[str, str]) -> str:
    """The page's rule: the document (and page) the finding points at, or the month's ledger."""
    doc_id = f.get("docId") or next((e["docId"] for e in f.get("evidence", []) if e.get("docId")), None)
    if not doc_id:
        return words(RISK_WORDS, "table.wholeMonth")
    file = files.get(doc_id, doc_id)
    if f["scope"] == "MONTH":
        return words(RISK_WORDS, "table.monthDocument", month=month_name(f["month"], "long"), file=file)
    page = next((e["page"] for e in f.get("evidence", []) if e.get("docId") == doc_id and e.get("page")), None)
    return words(RISK_WORDS, "table.documentPage", file=file, page=page) if page else words(RISK_WORDS, "table.document", file=file)


def finding_status(f: dict) -> tuple[str, str]:
    """(label, tone): a held copy waits; an open critical or high finding is bad; open medium waits."""
    if f["category"] == "DUPLICATE" and f["status"] == "OPEN":
        return words(RISK_WORDS, "status.held"), "wait"
    label = words(RISK_WORDS, f"status.{f['status'].lower()}")
    if f["status"] != "OPEN":
        return label, ""
    return label, "bad" if f["severity"] in ("CRITICAL", "HIGH") else "wait" if f["severity"] == "MEDIUM" else ""


def risk() -> str:
    files = {d["docId"]: d["fileName"] for d in RISK["documents"]}
    shown = [f for f in RISK["findings"] if f["status"] in ("OPEN", "ACKNOWLEDGED")]
    levels = {m["month"]: m.get("riskLevel") for m in DASH["months"]}
    by_month: dict[str, list[dict]] = {}
    for f in shown:
        by_month.setdefault(f["month"], []).append(f)
    group_level = {m: levels.get(m) or min(fs, key=lambda f: SEV_RANK[f["severity"]])["severity"] for m, fs in by_month.items()}
    ordered_months = sorted(by_month, key=lambda m: (SEV_RANK[group_level[m]], m))
    groups = []
    for month in ordered_months:
        rows = sorted(by_month[month], key=lambda f: (SEV_RANK[f["severity"]], f["code"], f["findingId"]))
        trs = []
        for f in rows:
            where = finding_where(f, files)
            label, tone = finding_status(f)
            trs.append(
                f'<tr{" class=\"is-flagged\"" if f["severity"] == "CRITICAL" else ""}><td><a class="find-link" href="evidence-viewer.html">{sev_badge(f["severity"])}'
                f'<span class="code-tag">{escape(f["code"].split("_")[0])}</span><span class="find-t">{escape(f["title"])}</span></a><span class="sub">{where}</span></td>'
                f'<td class="hide-rt">{where}</td><td class="r"><span class="status-line {tone}">{label}</span></td></tr>'
            )
        heading = month_name(month)
        groups.append(f"""
<section class="find-group" aria-label="{heading}">
  <div class="find-head"><h2 class="type-h3">{heading}</h2>{sev_badge(group_level[month])}<a class="link" href="month.html">{words(RISK_WORDS, "openMonth", month=month_name(month, "long"))}</a></div>
  <div class="table-panel rt-wrap"><table class="data-table rt find-table">
    <thead><tr><th>{words(RISK_WORDS, "table.finding")}</th><th class="hide-rt">{words(RISK_WORDS, "table.where")}</th><th class="r">{words(RISK_WORDS, "table.status")}</th></tr></thead>
    <tbody>{"".join(trs)}</tbody></table></div>
</section>""")
    counts = [
        ("all", len(shown)),
        *((lvl.lower(), sum(1 for f in shown if f["severity"] == lvl)) for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW")),
        ("held", sum(1 for f in shown if f["category"] == "DUPLICATE")),
    ]
    chips = "".join(f'<a class="chip" href="risk.html"{" aria-pressed=\"true\"" if i == 0 else ""}>{words(RISK_WORDS, f"filters.{key}")} <span class="n">{n}</span></a>'
                    for i, (key, n) in enumerate(counts))
    attention = [m for m in DASH["months"] if m.get("riskLevel") in ("CRITICAL", "HIGH")]
    if attention:
        lead = words(RISK_WORDS, "attention", count=len(attention), list=and_list([
            words(RISK_WORDS, "monthIs", month=month_name(m["month"], "long"), level=RISK_WORDS["severity"][m["riskLevel"]].lower())
            for m in attention]))
    else:
        lead = words(RISK_WORDS, "attentionNone")
    clean = [month_name(m["month"], "long") for m in DASH["months"] if m["month"] not in by_month]
    foot = f'<p class="muted small">{words(RISK_WORDS, "cleanMonths", count=len(clean), months=and_list(clean))}</p>' if clean else ""
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">{words(RISK_WORDS, "title")}</h1>
    <p><strong>{lead}</strong> {words(RISK_WORDS, "subtitle")}</p>
  </div>
  <div class="stack gap-6">
    <section aria-label="{words(RISK_WORDS, "riskByMonth")}">{month_tabs()}</section>
    <div class="chips" role="group" aria-label="{words(RISK_WORDS, "filterBySeverity")}">{chips}</div>
    {''.join(groups)}
    {foot}
  </div>
</div>"""
    return shell("risk", topbar("Risk", ("Risk",)), content)


# ------------------------------------------------------------------------------------------------
# Clients and suppliers
# ------------------------------------------------------------------------------------------------

CP = json.loads((ROOT / "contracts/design/fixtures/counterparties.json").read_text(encoding="utf-8"))
CP_WORDS = json.loads((LOCALES / "counterparties.json").read_text(encoding="utf-8"))
MONTH_WORDS_CP = json.loads((LOCALES / "months.json").read_text(encoding="utf-8"))
ROLE_ORDER = ("CLIENT", "SUPPLIER", "LENDER", "OWNER", "OWN_ACCOUNT", "GOVERNMENT", "RELATED_PARTY", "OTHER")
KIND_ICON_CP = {"BUSINESS": "building", "BANK": "bank", "PERSON": "user", "GOVERNMENT": "building", "UNKNOWN": "users"}


def _millions(amount: str) -> str:
    return f"{Decimal(amount) / Decimal(1_000_000):,.1f}"


def _transfers(party: dict) -> int:
    return sum(int(t.get("count", 0)) for t in party.get("totalsByMonth", {}).values())


def _money_in(party: dict) -> bool:
    return Decimal(party["totalIn"]["amount"]) >= Decimal(party["totalOut"]["amount"])


def _range(parties: list[dict]) -> str:
    months = sorted(m for p in parties for m in p.get("totalsByMonth", {}))
    if not months:
        return ""
    first, last = month_name(months[0], "short"), month_name(months[-1], "short")
    return first if first == last else f"{first} to {last}"


def clients() -> str:
    """The app's CounterpartiesPage on the shared fixture (spec 014; parity: counterparties.spec.ts)."""
    parties = CP["counterparties"]
    total_in = sum(Decimal(p["totalIn"]["amount"]) for p in parties)
    total_out = sum(Decimal(p["totalOut"]["amount"]) for p in parties)
    trs = []
    for p in parties:
        inward = _money_in(p)
        value = Decimal(p["totalIn"]["amount"] if inward else p["totalOut"]["amount"])
        amt = (
            f'<span class="{"amt-in" if inward else "amt-out"}">{"+" if inward else "−"}{_millions(str(value))}</span>'
            if value
            else '<span class="muted">0.0</span>'
        )
        total = total_in if inward else total_out
        share = (value / total * 100) if total else Decimal(0)
        accounts = sorted(p.get("accountsSeen", []), key=lambda a: a["firstSeen"])
        transfers = _transfers(p)
        flag = ""
        if len(accounts) >= 2:
            flag = (
                f'<a class="badge badge-high" href="risk.html">{icon("triangle-alert", "icon icon-sm")}'
                f'{words(CP_WORDS, "newAccount", month=month_name(accounts[-1]["firstSeen"][:7], "long"))}</a>'
            )
        elif p.get("openInvoices", 0) and transfers == 0:
            flag = (
                f'<a class="badge badge-medium" href="risk.html">{icon("circle-alert", "icon icon-sm")}'
                f'{words(CP_WORDS, "unpaid", count=p["openInvoices"])}</a>'
            )
        roles = ", ".join(words(CP_WORDS, f"roles.{r}") for r in p["roles"])
        trs.append(
            f"""<tr{' class="is-flagged"' if len(accounts) >= 2 else ""}>
  <td data-cell="wide"><span class="doc-cell"><span class="thumb">{icon(KIND_ICON_CP.get(p.get("kind", "UNKNOWN"), "users"), "icon icon-sm")}</span><span><strong>{escape(p["name"])}</strong><span class="sub">{escape(roles)}</span></span></span></td>
  <td class="r">{amt}</td>
  <td class="hide-rt"><span class="share"><span class="meter-bar"><i style="width:{min(Decimal(100), share * 3):.0f}%"></i></span><span>{share:.1f}%</span></span></td>
  <td class="r hide-rt">{transfers}</td>
  <td>{words(CP_WORDS, "accounts", count=len(accounts))} {flag}</td>
</tr>"""
        )
    counts = {r: sum(1 for p in parties if r in p["roles"]) for r in ROLE_ORDER}
    chip_items = [(words(CP_WORDS, "all"), len(parties))] + [
        (words(CP_WORDS, f"rolesPlural.{r}"), n) for r, n in counts.items() if n
    ]
    chips = "".join(
        f'<button type="button" class="chip" aria-pressed="{"true" if i == 0 else "false"}">{escape(label)} <span class="n">{n}</span></button>'
        for i, (label, n) in enumerate(chip_items)
    )
    columns = (
        words(CP_WORDS, "colName"),
        words(CP_WORDS, "colAmount", currency="IDR", range=_range(parties)),
        words(CP_WORDS, "colShare"),
        words(CP_WORDS, "colTransfers"),
        words(CP_WORDS, "colAccounts"),
    )
    content = f"""
<div class="page stack gap-6">
  <header class="page-head stack gap-2">
    <h1 class="type-title">{words(CP_WORDS, "title")}</h1>
    <p class="muted">{words(CP_WORDS, "subtitle")}</p>
  </header>
  <div class="stack gap-3">
    <div class="table-actions"><div class="search"><input type="search" placeholder="{words(CP_WORDS, "search")}" aria-label="{words(CP_WORDS, "search")}"></div>
      <div class="chips" role="group" aria-label="{words(CP_WORDS, "filterLabel")}">{chips}</div></div>
    <div class="table-panel rt-wrap"><table class="data-table rt">
      <thead><tr><th>{columns[0]}</th><th class="r">{columns[1]}</th><th class="hide-rt">{columns[2]}</th><th class="r hide-rt">{columns[3]}</th><th>{columns[4]}</th></tr></thead>
      <tbody>{"".join(trs)}</tbody></table></div>
    <p class="muted small">{words(CP_WORDS, "footnote")}</p>
  </div>
</div>"""
    return shell("clients", topbar(words(CP_WORDS, "title"), (words(CP_WORDS, "title"),)), content)


def counterparty() -> str:
    """One client or supplier (the app's CounterpartyPage) on the shared fixture."""
    detail = CP["detail"]
    party = next(p for p in CP["counterparties"] if p["counterpartyId"] == detail["counterpartyId"])
    w = lambda key, **kw: words(CP_WORDS, f"detail.{key}", **kw)  # noqa: E731
    roles = ", ".join(words(CP_WORDS, f"roles.{r}") for r in party["roles"])
    aliases = f' · {w("aliases", aliases=", ".join(party["aliases"]))}' if party.get("aliases") else ""
    figures = "".join(
        f'<div class="figure"><dt>{label}</dt><dd class="v">{value}</dd></div>'
        for label, value in (
            (w("moneyIn"), money_code(party["totalIn"]["amount"])),
            (w("moneyOut"), money_code(party["totalOut"]["amount"])),
            (w("openInvoices"), str(party.get("openInvoices", 0))),
            (w("firstSeen"), fmt_date(party["firstDate"])),
            (w("lastSeen"), fmt_date(party["lastDate"])),
        )
    )
    def cell(value: str, kind: str = "", right: bool = False) -> str:
        attrs = f' data-cell="{kind}"' if kind else ""
        cls = ' class="r"' if right else ""
        return f"<td{cls}{attrs}>{value}</td>"

    months = "".join(
        f"<tr>{cell(month_name(m), 'wide')}{cell(f'<span class=\"amt-in\">{money_code(t['in']['amount'])}</span>', right=True)}"
        f"{cell(f'<span class=\"amt-out\">{money_code(t['out']['amount'])}</span>', right=True)}{cell(str(t['count']), 'hide', right=True)}</tr>"
        for m, t in sorted(party["totalsByMonth"].items())
    )
    accounts = "".join(
        f"<tr>{cell(a['accountMasked'], 'wide')}{cell(fmt_date(a['firstSeen']))}{cell(fmt_date(a['lastSeen']), right=True)}</tr>"
        for a in party["accountsSeen"]
    )
    lines = "".join(
        f"<tr>{cell(escape(ln['description']), 'wide')}{cell(fmt_date(ln['date']))}"
        f"{cell(f'<span class=\"{'amt-in' if not ln['amount']['amount'].startswith('-') else 'amt-out'}\">{money_code(ln['amount']['amount'])}</span>', right=True)}</tr>"
        for ln in detail["lines"]
    )
    docs = "".join(
        f"<tr>{cell(f'<a class=\"link\" href=\"document.html\">{escape(inv['number'])}</a>', 'wide')}{cell(fmt_date(inv['issueDate']))}"
        f"{cell(money_code(inv['total']['amount']), right=True)}{cell(words(MONTH_WORDS_CP, f'monthDetail.payment.{inv['evidence']['payment']}'), 'wide')}</tr>"
        for inv in detail["invoices"]
    )

    def panel(hid: str, title: str, head: tuple[tuple[str, str], ...], rows: str) -> str:
        ths = "".join(
            f'<th{" class=\"r\"" if kind == "r" else " class=\"hide-rt\"" if kind == "hide" else ""}'
            f'{" data-cell=\"hide\"" if kind == "hide" else " data-cell=\"wide\"" if kind == "wide" else ""}>{label}</th>'
            for label, kind in head
        )
        return f"""<section class="panel" aria-labelledby="{hid}"><div class="panel-head"><h2 id="{hid}">{title}</h2></div>
  <div class="table-panel rt-wrap"><table class="data-table rt"><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table></div></section>"""

    content = f"""
<div class="page stack gap-6">
  <header class="page-head stack gap-2">
    <a class="link small" href="clients.html">{icon("chevron-left", "icon icon-sm")}{w("back")}</a>
    <h1 class="type-title">{escape(party["name"])}</h1>
    <p class="muted">{escape(roles)}{escape(aliases)}</p>
  </header>
  <section class="ledger" aria-label="{w("moneyIn")}"><dl class="ledger-figures">{figures}</dl></section>
  {panel("cp-months-h", w("months"), ((w("colMonth"), "wide"), (w("colIn"), "r"), (w("colOut"), "r"), (w("colCount"), "hide")), months)}
  {panel("cp-accounts-h", w("accounts"), ((w("colAccount"), "wide"), (w("colFirst"), ""), (w("colLast"), "r")), accounts)}
  {panel("cp-lines-h", w("lines"), ((w("colDescription"), "wide"), (w("colDate"), ""), (w("colAmountLine"), "r")), lines)}
  {panel("cp-docs-h", w("documents"), ((w("colDocument"), "wide"), (w("colDate"), ""), (w("colTotal"), "r"), (w("colPayment"), "wide")), docs)}
</div>"""
    return shell("clients", topbar(party["name"], (words(CP_WORDS, "title"), party["name"]), back=(words(CP_WORDS, "title"), "clients.html")), content)


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
    <div class="spread"><h1 class="type-title">Labels</h1><span class="badge badge-outline">Design only (P1, spec 016 · Placeholder at /labels)</span></div>
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
    <div class="spread"><h1 class="type-title">Runs</h1><div class="row" style="gap:var(--k-space-2)"><span class="badge badge-outline">Design only (P1, spec 017 · Placeholder at /runs)</span><span class="badge badge-outline">Owner only</span></div></div>
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


SCREENS_MORE = {
    "risk": ("Risk", risk),
    "clients": ("Clients and suppliers", clients),
    "counterparty": ("Client or supplier", counterparty),
    "labels": ("Labels", labels),
    "runs": ("Runs", runs),
}
NOTES_MORE = {
    "risk": "Findings grouped by month with their severity and status; each opens the evidence viewer.",
    "clients": "Clients and suppliers built from the books; a supplier paid to a new account is flagged.",
    "counterparty": "One client or supplier: totals by month, accounts seen with first and last use, its bank lines and documents.",
    "labels": "Every AI decision a person can check, lowest confidence first, with per-page types, extraction files, runs and dataset use.",
    "runs": "Run history like a tracing tool: runs, a span waterfall, and the selected model call with its request, response and label.",
}
