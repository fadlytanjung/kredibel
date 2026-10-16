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
# Labels (spec 016): drawn from contracts/design/fixtures/labels.json with the app's own words
# ------------------------------------------------------------------------------------------------

LABELS_FIX = json.loads((ROOT / "contracts/design/fixtures/labels.json").read_text(encoding="utf-8"))
LABEL_WORDS = json.loads((LOCALES / "labels.json").read_text(encoding="utf-8"))
MONTHS_WORDS = json.loads((LOCALES / "months.json").read_text(encoding="utf-8"))
DOCS_WORDS = json.loads((LOCALES / "documents.json").read_text(encoding="utf-8"))
MONTH_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def lw(key: str, **params) -> str:
    return words(LABEL_WORDS, key, **params)


def value_word(task: str, value: str) -> str:
    table = {"CATEGORY": MONTHS_WORDS["categories"], "DOC_TYPE": DOCS_WORDS["detail"]["docType"],
             "PAGE_TYPE": LABEL_WORDS["pageTypes"], "COUNTERPARTY_ROLE": LABEL_WORDS["roles"]}.get(task)
    return escape(table.get(value, value) if table else value)


def short_model(model: str | None) -> str:
    if not model:
        return ""
    low = model.lower()
    return "Flash-Lite" if "flash-lite" in low else "Flash" if "flash" in low else "Pro" if "pro" in low else model


def source_word(label: dict) -> str:
    ai = label["ai"]
    if ai["source"] == "MODEL":
        return lw("sources.MODEL", model=short_model(ai["model"]), prompt=ai["promptVersion"]) if ai.get("model") and ai.get("promptVersion") else lw("sources.MODEL_NO_VERSION")
    return lw(f"sources.{ai['source']}")


def status_key(label: dict) -> str:
    return {"VERIFIED": "verified", "CORRECTED": "corrected"}.get(label["status"], "needs" if label["needsCheck"] else "proposed")


def status_pill(label: dict) -> str:
    key = status_key(label)
    ic = icon("check", "icon icon-sm") if key in ("verified", "corrected") else ""
    word = lw("status.needs") if key == "needs" else lw(f"status.{label['status']}")
    return f'<span class="lbl-status {key}">{ic}{word}</span>'


def conf(v: float | None) -> str:
    if v is None:
        return f'<span class="conf none">{lw("noScore")}</span>'
    lvl = "lo" if v < 0.7 else "mid" if v < 0.9 else "hi"
    return f'<span class="conf {lvl}"><span class="conf-bar"><i style="width:{round(v * 100)}%"></i></span><span>{v:.2f}</span></span>'


def fmt_day(iso: str | None) -> str:
    return fmt_date(iso[:10]) if iso else ""


def page_chips(label: dict, items: list[dict]) -> str:
    doc = label["subject"].get("docId")
    if not doc:
        return ""
    pages = sorted((l for l in items if l["task"] == "PAGE_TYPE" and l["subject"].get("docId") == doc and l["subject"].get("pageNo")), key=lambda l: l["subject"]["pageNo"])
    if not pages:
        return ""
    chips = []
    for l in pages:
        c = l["ai"]["confidence"] or 0
        lvl = "lo" if c < 0.7 else "mid" if c < 0.9 else "hi"
        chips.append(f'<a class="pchip {lvl}" href="labels.html" title="{lw("pageChip", type=value_word("PAGE_TYPE", l["final"]["value"]), confidence=f"{c:.2f}")}">p{l["subject"]["pageNo"]} {value_word("PAGE_TYPE", l["final"]["value"])} <b>{c:.2f}</b></a>')
    return f'<span class="page-chips" aria-label="{lw("pageChips")}">{"".join(chips)}</span>'


def label_panel(label: dict) -> str:
    task, ai = label["task"], label["ai"]
    details = [lw("panel.month", month=MONTH_LONG[int(label["month"][5:7]) - 1]) if label.get("month") else None,
               f'p{label["subject"]["pageNo"]}' if label["subject"].get("pageNo") else None,
               lw("panel.cashflow", framework=(label.get("framework") or "").replace("_", " "), cashflow=words(MONTHS_WORDS, f"cashflow.{label['cashflowClass']}")) if label.get("framework") and label.get("cashflowClass") else None]
    details = [d for d in details if d]
    options = {"CATEGORY": list(MONTHS_WORDS["categories"]), "DOC_TYPE": ["BANK_STATEMENT", "SALES_INVOICE", "PURCHASE_INVOICE", "RECEIPT", "LEDGER_EXPORT", "OTHER"],
               "PAGE_TYPE": list(LABEL_WORDS["pageTypes"]), "COUNTERPARTY_ROLE": list(LABEL_WORDS["roles"])}.get(task)
    if options:
        field = f'<select class="select" id="lp-value">' + "".join(f'<option value="{o}"{" selected" if o == label["final"]["value"] else ""}>{value_word(task, o)}</option>' for o in options) + "</select>"
    else:
        field = f'<input class="input" id="lp-value" value="{escape(label["final"]["value"])}"/>'
    decided = f'<span class="sub">{lw("panel.decidedBy", status=lw(f"status.{label['status']}"), by=label.get("decidedBy") or "", when=fmt_day(label.get("decidedAt")))}</span>' if label["status"] != "AI_PROPOSED" else ""
    similar = f'<label class="check-row"><input type="checkbox" checked/> {lw("panel.applySimilar")}</label>' if task == "CATEGORY" and label["subject"].get("txId") else ""
    run = f'<a href="runs.html">{label["ai"]["runId"]}</a>{", " + lw("panel.span", span=ai["spanId"]) if ai.get("spanId") else ""}' if ai.get("runId") else "—"
    dataset = lw("panel.datasetExcluded") if label["dataset"]["use"] == "EXCLUDED" else lw(f"dataset.{label['dataset']['use']}")
    page = label["subject"].get("pageNo") or 1
    md = (LABELS_FIX.get("extractions") or {}).get(label.get("extractionUrl") or "")
    extraction_head = lw("panel.extractionOf", page=page) if label.get("extractionUrl") else lw("panel.extraction")
    extraction_body = (f'<pre tabindex="0" aria-label="{extraction_head}">{escape(md)}</pre>'
                       if md else f'<p class="muted small">{lw("panel.noExtraction")}</p>')
    download = f'<button type="button" class="button button-quiet button-sm">{icon("download", "icon icon-sm")}{lw("panel.downloadExtraction", page=page)}</button>' if md else ""
    return f"""
<aside class="lbl-panel panel" aria-labelledby="lp-h">
  <div class="lp-main">
  <div class="lp-head"><span class="task">{lw(f"tasks.{task}")}</span>{status_pill(label)}<a class="icon-button icon-button-sm ml-auto" href="labels.html" aria-label="{lw("panel.close")}">{icon("x", "icon icon-sm")}</a></div>
  <h2 id="lp-h" class="type-h3">{escape(label["subject"]["display"])}</h2>
  {f'<p class="muted small">{" · ".join(details)}</p>' if details else ""}
  <div class="lp-ai">
    <div><span class="k">{lw("panel.aiProposed")}</span><strong>{value_word(task, ai["value"])}</strong>{decided}</div>
    {conf(ai["confidence"])}
  </div>
  <div class="field"><label for="lp-value">{lw(f"panel.correctLabel.{task}")}</label>{field}</div>
  {similar}
  <div class="field"><label for="lp-note">{lw("panel.note")} <span class="muted">{lw("panel.noteOptional")}</span></label><input class="input" id="lp-note" placeholder="{lw("panel.notePlaceholder")}"/></div>
  <div class="row lp-actions"><a class="button button-primary" href="labels.html">{icon("check", "icon icon-sm")}{lw("panel.confirm")}</a><a class="button button-secondary" href="labels.html">{lw("panel.saveCorrection")}</a></div>
  </div>
  <div class="lp-side">
  <details class="lp-md" open><summary>{icon("markdown", "icon icon-sm")}{extraction_head}</summary>{extraction_body}<div class="row gap-3 flex-wrap">{download}{f'<a class="link small" href="document.html">{lw("openPage")}</a>' if label["subject"].get("docId") else ""}</div></details>
  <dl class="lp-prov">
    <div><dt>{lw("panel.model")}</dt><dd>{short_model(ai.get("model")) or "—"}</dd></div>
    <div><dt>{lw("panel.prompt")}</dt><dd>{escape(ai.get("promptVersion") or "—")}</dd></div>
    <div><dt>{lw("panel.run")}</dt><dd>{run}</dd></div>
    <div><dt>{lw("panel.datasetUse")}</dt><dd>{dataset}</dd></div>
  </dl>
  </div>
</aside>"""


def labels() -> str:
    items = LABELS_FIX["items"]
    summary = LABELS_FIX["summary"]
    selected = items[3]
    trs = []
    for label in items:
        s = label["subject"]
        sub = " · ".join(x for x in [MONTH_LONG[int(label["month"][5:7]) - 1] if label.get("month") else None, f'p{s["pageNo"]}' if s.get("pageNo") else None, s.get("field")] if x)
        decided = ""
        if label["status"] != "AI_PROPOSED":
            parts = [lw("decided", by=label.get("decidedBy") or "", when=fmt_day(label.get("decidedAt")))]
            if label["status"] == "CORRECTED":
                parts.append(lw("was", value=value_word(label["task"], label["ai"]["value"])))
            decided = f'<span class="sub">{". ".join(parts)}</span>'
        ext = (f'<a class="md-link" href="labels.html" title="{lw("openExtraction", page=s.get("pageNo") or 1)}">{icon("markdown", "icon icon-sm")}{lw("extractionFile", page=s.get("pageNo") or 1)}</a>'
               if label.get("extractionUrl") else f'<span class="muted">{lw("noExtraction")}</span>')
        run = f'<a class="run-link" href="runs.html">run …{label["ai"]["runId"][-4:]}</a>' if label["ai"].get("runId") else '<span class="muted">—</span>'
        trs.append(f"""<tr class="is-clickable{" is-selected" if label is selected else ""}">
  <td class="chk hide-rt"><input type="checkbox" aria-label="{lw("selectRow", subject=s["display"])}"{" disabled" if label["status"] != "AI_PROPOSED" else ""}/></td>
  <td data-cell="wide"><span class="lbl-subj"><strong>{escape(s["display"])}</strong>{f'<span class="sub">{sub}</span>' if sub else ""}{page_chips(label, items)}</span></td>
  <td data-cell="wide"><span class="task">{lw(f"tasks.{label['task']}")}</span><span class="lbl-val">{value_word(label["task"], label["final"]["value"])}</span>{decided}</td>
  <td>{conf(label["ai"]["confidence"])}</td>
  <td>{status_pill(label)}</td>
  <td class="hide-rt small muted">{source_word(label)}</td>
  <td class="hide-rt">{ext}</td>
  <td class="hide-rt">{run}</td>
  <td class="hide-rt"><span class="ds {label['dataset']['use'].lower()}">{lw(f"dataset.{label['dataset']['use']}")}</span></td>
</tr>""")
    total = summary["total"]
    n = lambda v: f"{v:,}"  # noqa: E731
    tasks = seg("task", [("all", f'{lw("tasks.all")} {n(total)}')] + [(k, f'{lw(f"tasks.{k}")} {n(summary["byTask"][k])}') for k in ("DOC_TYPE", "PAGE_TYPE", "CATEGORY", "COUNTERPARTY_ROLE", "FIELD_VALUE")], "all", lw("taskLabel"))
    needs = summary["needsCheck"]
    counts = [("needs", needs), ("proposed", max(summary["byStatus"]["AI_PROPOSED"] - needs, 0)), ("verified", summary["byStatus"]["VERIFIED"]), ("corrected", summary["byStatus"]["CORRECTED"])]
    chips = "".join(f'<a class="chip" href="labels.html" aria-pressed="false">{lw(f"statuses.{k}")} <span class="n">{n(v)}</span></a>' for k, v in counts)
    checked = summary["verified"] + summary["corrected"]
    lead = lw("lead", checked=n(checked), total=n(total), agreement=f'{summary["aiAgreementOnChecked"] * 100:.1f}%') if checked and summary.get("aiAgreementOnChecked") is not None else lw("leadNoneChecked")
    content = f"""
<div class="page">
  <div class="page-head">
    <h1 class="type-title">{lw("title")}</h1>
    <p><strong>{lead} {lw("needCheck", count=needs)}</strong> {lw("intro")}</p>
  </div>
  <div class="stack gap-3">
    <div class="spread lbl-tools">{tasks}<span class="fw-pill">{icon("book", "icon icon-sm")}{lw("framework", framework="IFRS")} <a href="plan-usage.html">{lw("changeFramework")}</a></span></div>
    <div class="chips" role="group" aria-label="{lw("statusFilter")}">{chips}</div>
    <div class="bulk-bar"><span><strong>{lw("selected", count=0)}</strong></span><button class="button button-secondary button-sm" type="button" disabled>{icon("check", "icon icon-sm")}{lw("confirmSelected")}</button><span class="muted small">{lw("bulkHint")}</span></div>
    <div class="lbl-layout">
      <div class="table-panel rt-wrap"><table class="data-table rt lbl-table">
        <thead><tr><th class="chk hide-rt"><span class="sr-only">{lw("columns.select")}</span></th><th>{lw("columns.subject")}</th><th>{lw("columns.label")}</th><th>{lw("columns.confidence")}</th><th>{lw("columns.status")}</th><th class="hide-rt">{lw("columns.source")}</th><th class="hide-rt">{lw("columns.extraction")}</th><th class="hide-rt">{lw("columns.run")}</th><th class="hide-rt">{lw("columns.dataset")}</th></tr></thead>
        <tbody>{''.join(trs)}</tbody></table></div>
      {label_panel(selected)}
    </div>
    <div class="spread lbl-foot"><p class="muted small">{lw("foot", shown=n(len(items)), total=n(total))}</p>
      <button class="button button-secondary button-sm" type="button" disabled>{icon("download", "icon icon-sm")}{lw("exportLater")}</button></div>
  </div>
</div>"""
    return shell("labels", topbar(lw("title"), (lw("title"),)), content)


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
# Runs (spec 017): drawn from contracts/design/fixtures/runs.json with the app's own words
# ------------------------------------------------------------------------------------------------

RUNS_FIX = json.loads((ROOT / "contracts/design/fixtures/runs.json").read_text(encoding="utf-8"))
RUN_WORDS = json.loads((LOCALES / "runs.json").read_text(encoding="utf-8"))
RUN_ICON = {"DOCUMENT": "files", "MONTH": "reconcile", "ASSISTANT": "sparkles"}
RUN_TONE = {"DONE": "ok", "RUNNING": "busy", "QUEUED": "wait", "SUPERSEDED": "wait", "FAILED": "bad"}
PROMPT_OF = {"classify_document": "classify", "read_page": "read_page", "categorize_bank_lines": "categorize",
             "propose_ledger_mapping": "map_ledger_columns", "explain_month": "explain", "assistant": "assistant"}


def rnw(key: str, **params) -> str:
    return words(RUN_WORDS, key, **params)


def _ts(iso: str | None) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() if iso else 0.0


def k_tokens(n: int | None) -> str:
    return f"{n / 1000:.1f}k" if n else "0"


def seconds(ms: float) -> str:
    return f"{ms / 1000:.1f} s"


def started_at(iso: str | None) -> str:
    from datetime import datetime
    if not iso:
        return "—"
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.day} {MONTH_LONG[d.month - 1][:3]}, {d.hour:02d}:{d.minute:02d}"


def duration_ms(run: dict) -> float:
    return max(0.0, (_ts(run.get("endedAt")) - _ts(run.get("createdAt"))) * 1000) if run.get("endedAt") else 0.0


def span_rows(run: dict) -> list[dict]:
    t0 = _ts(run["createdAt"])
    total = duration_ms(run)
    stages = run.get("stages") or []
    parents = {s["parent"] for s in stages if s.get("parent")}
    rows = [{"name": rnw("detail.root", workflow=rnw(f"detail.workflow.{run['kind']}")), "depth": 0, "kind": "wf", "start": 0.0, "end": total, "detail": escape(run["target"]), "stage": None}]
    for s in sorted(stages, key=lambda s: _ts(s.get("startedAt"))):
        start = (_ts(s.get("startedAt")) - t0) * 1000 if s.get("startedAt") else 0.0
        end = (_ts(s.get("endedAt")) - t0) * 1000 if s.get("endedAt") else start
        kind = "llm" if s.get("model") else "node" if s["node"] in parents else "code"
        detail = ": ".join(x for x in [f'{short_model(s["model"])}, {k_tokens(s.get("tokensIn"))} in, {k_tokens(s.get("tokensOut"))} out' if s.get("model") else None, s.get("summary")] if x)
        rows.append({"name": f'node:{s["node"]}', "depth": 2 if s.get("parent") else 1, "kind": kind, "start": start, "end": end, "detail": escape(detail), "stage": s})
    return rows


def runs() -> str:
    items = RUNS_FIX["items"]
    run = items[0]
    def llm_calls(r: dict) -> int:
        return sum(1 for s in (r.get("stages") or []) if s.get("model"))
    def labels_cell(r: dict) -> str:
        lb = r.get("labels") or {}
        parts = [rnw(f"labelsCell.{k}", count=lb[k]) for k in ("proposed", "verified", "corrected") if lb.get(k)]
        return ", ".join(parts) if parts else rnw("none")
    trs = []
    for r in items:
        usage = r.get("usage") or {}
        tokens = f'{k_tokens(usage.get("tokensIn"))} / {k_tokens(usage.get("tokensOut"))}' if usage.get("tokensIn") else rnw("none")
        models = ", ".join(short_model(m) for m in r.get("models") or []) or rnw("none")
        trs.append(f"""<tr class="is-clickable{" is-selected" if r is run else ""}">
  <td data-cell="wide"><span class="doc-cell"><span class="thumb">{icon(RUN_ICON.get(r["kind"], "files"))}</span><span><strong>{escape(r["target"])}</strong><span class="sub">{rnw("kindRun", kind=rnw(f"kinds.{r['kind']}"))}</span></span></span></td>
  <td><span class="status-line {RUN_TONE.get(r["status"], "")}">{rnw(f"status.{r['status']}")}</span></td>
  <td class="hide-rt">{started_at(r.get("createdAt"))}</td>
  <td class="r">{seconds(duration_ms(r)) if r.get("endedAt") else "—"}</td>
  <td class="r hide-rt">{llm_calls(r)}</td>
  <td class="r hide-rt">{tokens}</td>
  <td class="r hide-rt">{usage.get("estimatedUsd") or "0.000"}</td>
  <td class="hide-rt small">{models}</td>
  <td class="hide-rt small">{labels_cell(r)}</td>
</tr>""")
    counts = [("all", len(items))] + [(k, sum(1 for r in items if r["kind"] == k)) for k in ("DOCUMENT", "MONTH", "ASSISTANT")]
    counts += [("failed", sum(1 for r in items if r["status"] == "FAILED")), ("corrected", sum(1 for r in items if (r.get("labels") or {}).get("corrected")))]
    chips = "".join(f'<a class="chip" href="runs.html" aria-pressed="{str(k == "all").lower()}">{rnw(f"chips.{k}")} <span class="n">{n}</span></a>' for k, n in counts)
    rows = span_rows(run)
    total = max(rows[0]["end"], 1)
    chosen = next((r for r in rows if r["kind"] == "llm"), rows[0])
    lis = []
    for r in rows:
        left, width = r["start"] / total * 100, max((r["end"] - r["start"]) / total * 100, 0.6)
        lis.append(f"""<li class="span-row d{r["depth"]} {r["kind"]}{" sel" if r is chosen else ""}">
  <button type="button" class="span-name" aria-pressed="{str(r is chosen).lower()}">{r["name"]}</button>
  <span class="span-track"><i style="left:{left:.2f}%;width:{width:.2f}%"></i></span>
  <span class="span-dur">{seconds(r["end"] - r["start"])}</span>
  <span class="span-detail">{r["detail"]}</span>
</li>""")
    ticks = "".join(f'<span style="left:{s * 1000 / total * 100}%">{s} s</span>' for s in range(0, int(total // 1000) + 1, 10) if s * 1000 < total)
    stage = chosen["stage"]
    events = (RUNS_FIX.get("events") or {}).get(run["runId"], {}).get("items", [])
    label_ids = next((e["labelIds"] for e in events if stage and e["node"] == stage["node"] and e.get("spanId") == stage.get("traceSpanId") and e["eventType"] == ("LLM_RESPONSE" if stage.get("model") else "NODE_OUTPUT")), [])
    prompt = (run.get("promptVersions") or {}).get(PROMPT_OF.get(stage["node"], stage["node"])) if stage else None
    kind_word = rnw(f"detail.kind.{'node' if chosen['kind'] == 'wf' else chosen['kind']}")
    inspector = f"""
<aside class="ev-inspector panel" aria-labelledby="ev-h">
  <div class="lp-main">
  <div class="lp-head"><span class="task">{kind_word}</span></div>
  <h2 id="ev-h" class="type-h3">{chosen["name"]}</h2>
  <dl class="lp-prov">
    <div><dt>{rnw("detail.model")}</dt><dd>{short_model(stage.get("model")) if stage and stage.get("model") else "—"}</dd></div>
    <div><dt>{rnw("detail.prompt")}</dt><dd>{escape(prompt) if prompt else "—"}</dd></div>
    <div><dt>{rnw("detail.latency")}</dt><dd>{seconds(chosen["end"] - chosen["start"])}</dd></div>
    <div><dt>{rnw("detail.tokens")}</dt><dd>{rnw("detail.tokensValue", tokensIn=f"{stage.get('tokensIn') or 0:,}", tokensOut=f"{stage.get('tokensOut') or 0:,}") if stage and stage.get("model") else "—"}</dd></div>
    <div><dt>{rnw("detail.span")}</dt><dd>{rnw("detail.spanValue", span=stage["traceSpanId"], trace=(run.get("traceId") or "")[:4] + "…") if stage and stage.get("traceSpanId") else "—"}</dd></div>
  </dl>
  <div class="row">{f'<a class="button button-secondary button-sm" href="labels.html">{icon("tag", "icon icon-sm")}{rnw("detail.openLabel")}</a>' if label_ids else ""}{f'<a class="button button-quiet button-sm" href="{run["traceUrl"]}" target="_blank" rel="noreferrer">{icon("external", "icon icon-sm")}{rnw("detail.cloudTrace")}</a>' if run.get("traceUrl") else ""}</div>
  </div>
  <div class="lp-side"><p class="muted small">{rnw("detail.notCaptured")}</p></div>
</aside>"""
    usage = run.get("usage") or {}
    summary = rnw("detail.summary", started=started_at(run.get("createdAt")), duration=seconds(duration_ms(run)), calls=llm_calls(run), tokensIn=k_tokens(usage.get("tokensIn")), tokensOut=k_tokens(usage.get("tokensOut")), usd=usage.get("estimatedUsd") or "0.000", prompts=", ".join((run.get("promptVersions") or {}).values()) or rnw("detail.noPrompts"))
    content = f"""
<div class="page">
  <div class="page-head">
    <div class="spread"><h1 class="type-title">{rnw("title")}</h1><span class="badge badge-outline">{rnw("ownerOnly")}</span></div>
    <p>{rnw("intro")}</p>
  </div>
  <div class="stack gap-5">
    <div class="chips" role="group" aria-label="{rnw("filter")}">{chips}</div>
    <div class="table-panel rt-wrap"><table class="data-table rt runs-table">
      <thead><tr><th>{rnw("columns.run")}</th><th>{rnw("columns.status")}</th><th class="hide-rt">{rnw("columns.started")}</th><th class="r">{rnw("columns.duration")}</th><th class="r hide-rt">{rnw("columns.calls")}</th><th class="r hide-rt">{rnw("columns.tokens")}</th><th class="r hide-rt">{rnw("columns.usd")}</th><th class="hide-rt">{rnw("columns.models")}</th><th class="hide-rt">{rnw("columns.labels")}</th></tr></thead>
      <tbody>{''.join(trs)}</tbody></table></div>
    <section class="run-detail" aria-labelledby="rd-h">
      <div class="spread"><div><h2 class="type-h2" id="rd-h">{rnw("detail.title", workflow=rnw(f"detail.workflow.{run['kind']}"), target=run["target"])}</h2><p class="muted small">{summary}</p></div></div>
      <div class="run-layout">
        <div class="panel waterfall-panel">
          <div class="span-axis" aria-hidden="true"><span class="span-name"></span><span class="span-track">{ticks}</span></div>
          <ol class="spans">{''.join(lis)}</ol>
          <p class="span-legend"><span class="llm"><i></i>{rnw("detail.legend.llm")}</span><span class="code"><i></i>{rnw("detail.legend.code")}</span><span class="node"><i></i>{rnw("detail.legend.node")}</span></p>
        </div>
        {inspector}
      </div>
    </section>
  </div>
</div>"""
    return shell("runs", topbar(rnw("title"), (rnw("title"),)), content, fab=False)


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
