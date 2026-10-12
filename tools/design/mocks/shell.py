"""Shared shell for the Kredibel mocks: sidebar (large), rail (medium/expanded), top bar, bottom
navigation, the More sheet and the floating upload (compact). Every link points at another mock, so
the folder works as a clickable prototype. All content is synthetic (docs/18)."""

from icons import icon

BRAND = "../brand"

# key, icon, label, short label, href, count (text, neutral?)
NAV_MAIN = [("dashboard", "dashboard", "Dashboard", "Dashboard", "dashboard.html", None)]
NAV_BOOKS = [
    ("documents", "files", "Documents", "Documents", "documents.html", ("92", True)),
    ("months", "reconcile", "Reconciliation", "Reconcile", "month.html", None),
    ("review", "inbox", "Review", "Review", "review.html", ("9", False)),
    ("risk", "shield-alert", "Risk", "Risk", "risk.html", ("2", False)),
]
NAV_INSIGHT = [
    ("clients", "users", "Clients and suppliers", "Clients", "clients.html", None),
    ("assistant", "sparkles", "Assistant", "Assistant", "assistant.html", None),
]
NAV_AI = [
    ("labels", "tag", "Labels", "Labels", "labels.html", ("37", True)),
    ("runs", "flow", "Runs", "Runs", "runs.html", None),
]


def _item(key, ic, label, short, href, count, active):
    cur = ' aria-current="page"' if key == active else ""
    cnt = ""
    if count:
        n, neutral = count
        cnt = f'<span class="nav-count{" is-neutral" if neutral else ""}" aria-label="{n} items">{n}</span>'
    return (f'<a class="nav-item" href="{href}"{cur} title="{label}"><span class="nav-icon">{icon(ic)}</span>'
            f'<span class="nav-label-long hide-below-large">{label}</span>'
            f'<span class="nav-label-short hide-large">{short}</span>{cnt}</a>')


def side(active: str, currency: str = "IDR") -> str:
    main = "".join(_item(*n, active) for n in NAV_MAIN)
    books = "".join(_item(*n, active) for n in NAV_BOOKS)
    insight = "".join(_item(*n, active) for n in NAV_INSIGHT)
    ai = "".join(_item(*n, active) for n in NAV_AI)
    profile_current = ' aria-current="page"' if active == "settings" else ""
    return f"""<aside class="side">
  <a href="dashboard.html" aria-label="Kredibel home"><img class="lockup" src="{BRAND}/kredibel-logo.svg" alt="Kredibel"/><img class="side-mark" src="{BRAND}/kredibel-mark.svg" alt="Kredibel"/></a>
  <a class="workspace" href="plan-usage.html"><span class="ws-icon">{icon("building")}</span><span><strong>Sunrise Coffee Roasters</strong><span class="sub">Company, {currency}, IFRS</span></span>{icon("chevron-down", "icon icon-sm")}</a>
  <nav class="nav" aria-label="Main">{main}
    <span class="nav-group-label">Books</span>{books}
    <span class="nav-group-label">Insight</span><span class="nav-sep" aria-hidden="true"></span>{insight}
    <span class="nav-group-label">AI quality</span><span class="nav-sep" aria-hidden="true"></span>{ai}
  </nav>
  <div class="side-foot">
    <a class="trial-status" href="plan-usage.html" title="Plan and usage"><div class="trial-head"><strong>Free trial: 23 days left</strong><span class="pages">286 of 400 pages</span></div><span class="bar" aria-hidden="true"><i style="width:72%"></i></span></a>
    <a class="user" href="plan-usage.html"{profile_current} title="Settings" aria-label="Settings, signed in as Maya Sari (Owner)"><span class="avatar" aria-hidden="true">MS</span><span><strong>Maya Sari</strong>Owner</span>{icon("sliders", "icon user-action")}</a>
  </div>
</aside>"""


def bottom_nav(active: str) -> str:
    items = [
        ("dashboard", "dashboard", "Dashboard", "dashboard.html", None),
        ("documents", "files", "Documents", "documents.html", None),
        ("review", "inbox", "Review", "review.html", "9"),
        ("risk", "shield-alert", "Risk", "risk.html", "2"),
        ("more", "menu", "More", "#more", None),
    ]
    in_more = active in {"months", "clients", "assistant", "labels", "runs", "settings"}
    out = []
    for key, ic, label, href, n in items:
        cur = ' aria-current="page"' if key == active or (key == "more" and in_more) else ""
        badge = f'<span class="nav-count" aria-label="{n} open">{n}</span>' if n else ""
        out.append(f'<a class="nav-item" href="{href}"{cur}><span class="nav-icon">{icon(ic)}{badge}</span>{label}</a>')
    return f'<nav class="bottom-nav" aria-label="Main">{"".join(out)}</nav>'


def more_sheet() -> str:
    links = [
        ("reconcile", "Reconciliation", "month.html"), ("users", "Clients and suppliers", "clients.html"),
        ("sparkles", "Assistant", "assistant.html"), ("tag", "Labels", "labels.html"),
        ("flow", "Runs", "runs.html"), ("sliders", "Settings", "plan-usage.html"),
        ("book", "Logo and brand", "brand.html"), ("dashboard", "All screens", "index.html"),
    ]
    items = "".join(f'<a href="{h}">{icon(ic)}<span>{t}</span>{icon("chevron-right", "icon icon-sm")}</a>' for ic, t, h in links)
    return (f'<div class="more-sheet" id="more" role="dialog" aria-label="More"><a class="scrim" href="#" aria-label="Close"></a>'
            f'<div class="sheet"><span class="handle" aria-hidden="true"></span><p class="sheet-title">More</p>'
            f'<nav class="sheet-links">{items}</nav></div></div>')


def crumbs(*parts) -> str:
    """parts: strings or (text, href) pairs; the last part is the current page."""
    out = []
    for i, part in enumerate(parts):
        text, href = (part, "dashboard.html") if isinstance(part, str) else part
        if i < len(parts) - 1:
            out.append(f'<a href="{href}">{text}</a>{icon("chevron-right")}')
        else:
            out.append(f'<span aria-current="page">{text}</span>')
    return f'<nav class="crumbs" aria-label="Breadcrumb">{"".join(out)}</nav>'


def topbar(title: str, crumb_parts: tuple, back: tuple[str, str] | None = None, extra: str = "", upload: bool = True) -> str:
    """back: (label, href) for the compact back button."""
    if back:
        left = f'<a class="icon-button only-compact" href="{back[1]}" aria-label="Back to {back[0]}">{icon("chevron-left")}</a>'
    else:
        left = f'<a class="only-compact" href="dashboard.html"><img class="mark" src="{BRAND}/kredibel-mark.svg" alt="Kredibel"/></a>'
    up = (f'<a class="button button-primary hide-compact" href="documents.html">{icon("upload", "icon icon-sm")}Upload</a>' if upload else "")
    return f"""<header class="topbar">
  {left}
  <p class="topbar-title only-compact">{title}</p>
  {crumbs(*crumb_parts)}
  <div class="topbar-actions">
    {extra}
    <a class="search-field" href="#">{icon("search", "icon icon-sm")}Search books<span class="kbd">/</span></a>
    <a class="icon-button" href="risk.html" aria-label="Notifications, 2 new">{icon("bell")}<span class="dot"></span></a>
    {up}
  </div>
</header>"""


def shell(active: str, top: str, content: str, fab: bool = True, nav: bool = True, currency: str = "IDR") -> str:
    fab_html = f'<a class="fab" href="documents.html">{icon("upload")}Upload</a>' if fab else ""
    return (
        '<div class="viewport"><div class="app">'
        f'{side(active, currency)}'
        '<div class="main">'
        f'{top}'
        f'<main id="content">{content}</main>'
        f'<div class="dock">{fab_html}{bottom_nav(active) if nav else ""}</div>'
        '</div></div>'
        f'{more_sheet()}'
        '</div>'
    )


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Kredibel mock: {title}</title>
<meta name="description" content="High-fidelity mock with synthetic data. Tokens: contracts/design/tokens.json. Components: docs/12-design-system.md."/>
<link rel="icon" href="../brand/favicon.svg"/>
<link rel="stylesheet" href="assets/tokens.css"/>
<link rel="stylesheet" href="assets/kit.css"/>
<script src="assets/proto.js" defer></script>
</head>
<body>
{body}
</body>
</html>
"""
