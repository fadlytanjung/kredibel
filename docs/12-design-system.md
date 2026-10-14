# 12 — Design System

> **Concept: "Two readings."** Kredibel reads every printed figure twice and only counts it when both
> readings agree. The interface shows that idea everywhere: a figure two readings agree on carries a
> **double rule** (the accountant's mark for a final total); the mark itself is a stem (what was
> printed) with a tick growing out of it (the check); evidence is lit by a violet **lamp** over the
> exact printed value. Around that: cool paper surfaces, ink text, one ledger green for action, a mint
> that only ever means "checked", a strict severity scale, and a **money-flow** picture that shows a
> small business where its money went.

Version **2.1** of the tokens (friendlier radii, money-flow colours, a labelled sidebar; loan grades
removed). Mocks: [`design/mocks/`](../design/mocks/index.html) (open in a browser and resize;
screenshots in [`11-frontend.md`](11-frontend.md) §6). Tokens:
[`contracts/design/tokens.json`](../contracts/design/tokens.json).

---

## 0. How the design is built and changed (read first)

One direction of flow, so a design change is made once and lands everywhere:

```
contracts/design/tokens.json        the only place a colour, size, radius, shadow or duration is written
        │  make tokens  (tools/design/build_tokens.py: also checks contrast, fails on a low pair)
        ▼
frontend/src/app/styles/tokens.css           CSS variables  --k-*  (light; dark is opt-in, P2)
frontend/src/app/styles/tailwind-theme.css   Tailwind v4 @theme inline: bg-surface, text-ink, ...
design/mocks/assets/tokens.css               the same variables for the HTML mocks
        │
        ▼
design/mocks/assets/kit.css         THE component stylesheet (kebab-case classes), for mocks and app
        │  make tokens  copies it to frontend/src/app/styles/kit.css (ADR-019)
        ▼
frontend/src/shared/ui/*            React components that render the kit classes (cva variants map to
                                    kit modifiers), one story per state; Icon draws icons.py's set
        │
        ▼
widgets → pages                     the mock's markup with kit classes; Tailwind only for layout glue
```

| To change | Edit | Then |
|---|---|---|
| A colour, font size, radius, shadow, duration, breakpoint | `contracts/design/tokens.json` | `make tokens`; review the visual-regression diff; update §2–§4 here if a role changed |
| How a component looks | its class in `design/mocks/assets/kit.css` (one place for mocks and app, ADR-019) | `make tokens mocks mock-shots`; update the app's visual baselines in the same PR |
| How a component behaves | its file in `shared/ui/` and its stories | tests and stories |
| How a screen is laid out | the page or widget; the screen in `tools/design/mocks/screens.py` | `make mocks mock-shots`; check the three widths |
| The logo | `design/brand/*.svg` (never redraw from scratch) | `make mocks mock-shots` for the brand page |
| A rule (what we avoid, content style) | this document | the `/ui-screen` skill and rule `30-frontend` read it |

The design loop is the `/ui-screen` skill (`.agents/skills/ui-screen/SKILL.md`): spec → mock →
screenshots at 390, 834 and 1440 px → critique against §1 and §10 → component → stories → visual
baseline.

Every UI change updates its generated mock source and React implementation in the same change,
including text and empty/loading/error states. Regenerate mocks and shared CSS, capture affected
screens at 390/834/1440, inspect 360/1600 bounds, and update stories/visual baselines. A behaviour-only
change must still have a representative mock state; do not edit generated HTML or app kit.css.
`tools/checks/mock_sync.py` runs in `make check` and fails stale generated mock artifacts. Visual
parity remains a screenshot review; source freshness alone does not prove it.

P&L uses `.pnl-bars`, `.pnl-row`, `.pnl-track`, `.pnl-account` and `.pnl-source` from the kit. These
HTML bars keep readable labels at every width; bar width alone uses computed geometry. The report
shows signed values and source links; colours never imply that the books are complete or verified.

Gates that keep it honest ([`15`](15-testing-and-evaluation.md) §2.6): `make tokens-check` (generated
CSS is current, contrast pairs pass), `tools/checks/no_raw_styles.py` (no hex, `rgb()`, arbitrary
Tailwind values or inline styles outside the allow-list), Storybook interaction and axe tests,
Playwright visual regression at 390, 834 and 1440 px, Lighthouse CI budgets.

---

## 1. Principles

1. **Say where things stand first.** Each page opens with one plain sentence or figure; the detail
   follows.
2. **Evidence first.** Any figure, match or finding is one tap from the page and box it came from.
3. **Shape before colour.** Meaning is carried by a shape, icon or word; colour supports it (double,
   dotted and wavy rules; icons on every badge).
4. **One loud thing per screen.** On the dashboard it is the status sentence; on a month, its
   explanation; on evidence, the lamp. Everything around it is quiet.
5. **Numbers are the heroes.** Tabular, right-aligned, wide-set figures; units small and muted.
6. **Friendly, not cute.** Soft radii and plain words for a small-business owner; no mascots, no
   jokes about money.
7. **The phone is a real place to work.** Photograph a receipt, settle a review item, read a month on
   a 360 px screen.
8. **Honest about limits.** Disabled things say why; coming-soon things look unavailable, never
   broken.

**What we avoid** (each is a review comment waiting to happen):

- Labels in ALL CAPS or tracked-out small caps above headings. Use sentence case and the type scale.
- Meta strings joined with middle dots (`A · B · C`). Use a definition list or two short lines.
- Arrow glyphs appended to links or buttons ("See March →"). The verb is enough; icons go first.
- One word of a headline in another colour or italic.
- Content chopped into identical cards with the same soft shadow. Sections are separated by space and
  hairlines; only overlays and the floating upload button are raised.
- Gradient washes, emoji, decorative illustrations, stock photos.
- A monospace face for data. Codes use Archivo at a condensed width (§3).
- Colour as the only signal; red for anything that is not a problem; mint for anything that is not
  checked.

---

## 2. Colour

### 2.1 Files and names

`tokens.json` has three colour groups: `core` (raw palette), `light` and `dark` (semantic roles with
the same names). Components only use roles. CSS variables are `--k-color-<group>-<name>`; Tailwind
names are short:

| Role (under `light.color`) | Tailwind name | Light value | Use |
|---|---|---|---|
| `bg.canvas` | `canvas` | `#F2F4F5` | App background ("paper") |
| `bg.surface` | `surface` | `#FFFFFF` | Panels, tables, forms |
| `bg.sunken` | `sunken` | `#E8ECEE` | Table headers, wells, the evidence viewer |
| `bg.raised` | `raised` | `#FFFFFF` | Overlays: drawers, sheets, popovers |
| `bg.inverse` | `inverse` | `#16212B` | Tooltips, toasts, the onboarding brand panel ("ink") |
| `border.default` / `.strong` | `line`, `line-strong` | `#DCE1E5`, `#828E99` | Hairlines; inputs and boundaries (≥ 3:1) |
| `text.default` / `.muted` / `.subtle` | `ink`, `ink-muted`, `ink-subtle` | `#16212B`, `#56636F`, `#6B7782` | Text (all ≥ 4.5:1 on surface) |
| `brand.default` / `.hover` / `.soft` / `.line` | `brand`, `brand-hover`, `brand-soft`, `brand-line` | `#0E5A47`, `#0A4738`, `#E7F2EE`, `#2E8B6A` | Ledger green: primary actions, links, selection, reconciled |
| `brand.accent` | `brand-accent` | `#9FE0C6` | Check mint: the logo's tick, "kept in the account", ticks on dark surfaces. Never text on white |
| `evidence.line` / `.fill` / `.soft` / `.text` | `evidence-*` | `#6B4EFF`, 16% fill, `#F1EEFF`, `#4A2FCC` | The lamp, citation chips, AI suggestions |
| `focus.ring` | `focus` | `#5A3DF0` | 2 px ring, 2 px offset; violet so focus never reads as a status |

### 2.2 Severity, verdicts, readings

Severity text sits on its soft background (every pair ≥ 4.5:1, checked by `make tokens`). The icon is
from lucide; the text is always present. Fraud risk levels of months and documents use the same scale.

| Severity / risk level | Text | Soft bg | Line | Icon |
|---|---|---|---|---|
| Critical | `#B42318` | `#FDECEA` | `#F0857A` | `octagon-alert` |
| High | `#A6420A` | `#FEF0E1` | `#F2A766` | `triangle-alert` |
| Medium | `#7F5A00` | `#FFF5D6` | `#E8C25A` | `circle-alert` |
| Low | `#2F5C93` | `#E8EFF7` | `#8FB1DA` | `info` |
| Info | `#3B4652` | `#E8ECEE` | `#B9C2CA` | `circle-dot` |

| Document check (verdict) | Label on screen | Text / soft bg | Icon |
|---|---|---|---|
| `CLEAN` | Clean | `#17663F` / `#E3F3EA` | `shield-check` |
| `SUSPICIOUS` | Looks odd | `#7F5A00` / `#FFF5D6` | `shield-alert` |
| `TAMPERED` | Edited | `#B42318` / `#FDECEA` | `shield-x` |
| `UNVERIFIABLE` | Not checked (dashed border) | `#3B4652` / `#E8ECEE` | `shield-question` |

| Reading (provenance) | Mark under the figure | Colour | Meaning |
|---|---|---|---|
| `AGREED` | **double** rule | `#17714F` | The AI reader and the witness read the same value |
| `SINGLE_SOURCE` | **dotted** rule | `#828E99` | Only one reading has it |
| `CONFLICT` | **wavy** rule | `#B42318` | The readings disagree; never used for a CRITICAL accusation |

Match chips: **auto** (brand soft, link icon), **manual** (low soft, hand icon, "Matched by Maya on
12 Jul"), **proposed** (medium soft, "Choose a match"), **no match** (sunken, unlink icon).

Reconciliation evidence (ADR-025): **Bank recorded** is a neutral outline badge; **No supporting
document** and **Waiting for statement** use neutral chips. User approval/payment confirmation uses
the hand icon and always states whether bank evidence exists. Use `.seg-touch` for the evidence
view switcher (token touch-target height at every width); decision actions use `.button-lg`.

### 2.3 Charts

- **Money flow** (§6.4): bands in `chart.flow-in` (`#7DB9A2` at 55%) and `chart.flow-out` (`#B9C2CA`
  at 60%); the band under the pointer or focus in `chart.flow-hover`; nodes `chart.node-source`,
  `chart.node-account`, `chart.node-use`; **Kept in the account** in `chart.kept` (mint); when more
  went out than came in, **Taken from the account** is a source in `chart.taken` (amber).
- **Activities** (the statement view of the money flow, the bars and the cash-flow waterfall):
  `chart.operating` (slate), `chart.investing` (blue), `chart.financing` (violet-plum); kept money in
  `chart.kept`; opening and closing balances in `chart.node-account`. Colour is never the only cue:
  every band and bar is labelled with its activity or line.
- **Bars and lines** (months, the assistant's small charts): at most five series, each also
  differing in shape: money in `chart.inflow` bars, money out `chart.outflow` bars, net `chart.net`
  bars or solid line, balance `chart.balance` dashed line, negative days `chart.negative` markers;
  grid lines `chart.grid`. A month with a Critical or High risk gets a `severity.critical.line`
  outline, not a different fill.
- **One chart per row, full width.** A chart sits in a `ChartPanel` that takes the whole content
  width (beside the navigation, never under it); panels stack in one column and never share a row
  with another chart or card. A panel may switch views (`SegmentedControl`), never split into
  columns.
- **Three drawings per chart** chosen by the panel's width: compact (< 640 px), medium (640 to 959)
  and wide (≥ 960). Each has its own viewBox (380, 800 to 860, 1200 units) so chart text renders at
  12 to 15 px instead of being scaled down.
- Every chart has **Show as a table** (or a **Table** view) and a text summary for screen readers.

### 2.4 Dark mode (P2)

`dark` holds the same roles. `tokens.css` applies it only with `<html data-theme="dark">`, so it can
be reviewed screen by screen before it follows the system setting. No component has a dark variant;
if one needs it, a role is missing from the tokens.

---

## 3. Typography

One family, **Archivo** (variable, SIL OFL), self-hosted with `@fontsource-variable/archivo` (the
`wdth` file: weight 100–900, width 62–125%). Its width axis is the personality: wide for titles and
hero figures, normal for reading, condensed for codes. Every style is a `.type-*` class generated
from `tokens.json`.

| Style | Size / line (compact) | Weight | Width | Use |
|---|---|---|---|---|
| `type-figure-xl` | 40/44 (32/36) | 640 | 116% | The status sentence, trial days |
| `type-figure-lg` | 26/32 (22/28) | 620 | 108% | Figures on the dashboard and month |
| `type-figure-md` | 17/24 | 600 | 108% | Figures in lists, month tabs, candidates |
| `type-title` | 34/40 (26/32) | 680 | 116% | Page title ("Documents", "March 2026") |
| `type-h1` | 24/30 | 640 | 108% | Drawer and fix-panel titles |
| `type-h2` | 18/26 | 620 | 100% | Section titles |
| `type-h3` | 15/22 | 620 | 100% | Sub-sections |
| `type-body` | 15/22 (16/24) | 400 | 100% | Text |
| `type-body-sm` | 13/18 (14/20) | 400 | 100% | Notes, reasons, hints |
| `type-label` | 13/18 | 560 | 100% | Field and figure labels |
| `type-code` | 13/18 | 640 | 80% | `A01`, `GVF-2026-0311`, invoice numbers |

Rules: sentence case everywhere; numbers use `tabular-nums lining-nums` (utility `num`) and are
right-aligned in tables; units are smaller and muted (`IDR` before `1,355.8 M`); prose ≤ 72
characters; inputs are 16 px on compact screens (no zoom on focus in mobile browsers).

---

## 4. Space, shape, depth, motion

- **Space:** 4 px base: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64. Sections are separated by 32–40 px;
  related items by 8–16 px.
- **Radius follows hierarchy:** `xs` 6 (badges, code tags), `sm` 10 (buttons, inputs, rows, kind
  tiles), `md` 16 (panels, month tabs, candidates), `lg` 24 (sheets, drawers, the trial hero),
  `full` (pills, chips, avatars, the floating upload button).
- **Depth:** hairlines first. Two shadows only: `raised` (the floating upload button, the sticky fix
  bar on phones) and `overlay` (drawers, sheets, popovers, dialogs). Nothing else casts a shadow.
- **Motion:** `fast` 140 ms for hover and toggles, `base` 220 ms for tabs and sheets, `slow` 320 ms
  for drawers, easing `standard` `cubic-bezier(0.2, 0, 0, 1)`. **One orchestrated moment:** when the
  evidence viewer opens, the lamp sweeps once across the box (`sweep` 720 ms, 400 ms delay). Upload
  rows and month tabs tick as they finish. Nothing animates on its own after that. Everything respects
  `prefers-reduced-motion` (the sweep is removed, sheets cross-fade).

---

## 5. Layout and the responsive system

### 5.1 Window size classes

Breakpoints are tokens (`layout.breakpoint.*`) and Tailwind variants named after the class.

| Class | Width | Navigation | Gutter | Tailwind |
|---|---|---|---|---|
| Compact | < 600 | Top bar (mark or back, title, bell) + bottom navigation (Dashboard, Documents, Review, Risk, More) + floating **Upload** | 16 | default |
| Medium | 600–839 | Navigation rail (88 px, icon and short label) + top bar with breadcrumbs, search and **Upload** | 24 | `medium:` |
| Expanded | 840–1199 | Rail | 32 | `expanded:` |
| Large | ≥ 1200 | Labelled sidebar (248 px): logo, workspace, grouped navigation with counts, trial status, profile (opens Settings); fits 768 px tall without scrolling | 32 | `large:` |
| Wide | ≥ 1600 | Sidebar; content max 1280 px, left-aligned | 32 | `wide:` |

```
Compact (390)                 Medium / expanded (834)              Large (1440)
┌──────────────────────┐      ┌────┬──────────────────────────┐    ┌──────────┬──────────────────────────────────┐
│ k✓ Dashboard      🔔 │      │ k✓ │ Dashboard   🔔 [Upload]  │    │ k✓ kred… │ Dashboard  period search [Upload]│
├──────────────────────┤      │    ├──────────────────────────┤    │ Sunrise… ├──────────────────────────────────┤
│ Status sentence      │      │ Da │ Status sentence          │    │ Dashboard│ Status sentence        [Review]  │
│ Reasons, [Review]    │      │ Do │ Figures (2 columns)      │    │ Books    │ Figures (6 columns)              │
│ Figures (2 columns)  │      │ Re │ Needs you                │    │  Docs 92 │ ┌ Money flow ──────┐ ┌ Needs you ┐│
│ Needs you            │      │ Rv │ Risk                     │    │  Recon   │ │ Sankey           │ │           ││
│ Risk                 │      │ Ri │ Money flow (Sankey)      │    │  Review 8│ │                  │ ├ Risk ─────┤│
│ Money flow as bars   │      │ Cl │ Months (scroll)          │    │  Risk 2  │ └──────────────────┘ └───────────┘│
│ Months (scroll)  [⬆] │      │ As │                          │    │ Insight  │ Months: Jan Feb Mar Apr May Jun  │
├──────────────────────┤      │    │                          │    │ trial    │                                  │
│ Da  Do  Rv  Ri  More │      │ MS │                          │    │ Maya   ⚙ │                                  │
└──────────────────────┘      └────┴──────────────────────────┘    └──────────┴──────────────────────────────────┘
```

### 5.2 Components respond to their container

Page-level layout uses the window classes above; components use **container queries**, so the same
component works in the main column, a sheet or a drawer.

| Component | Container width | Behaviour |
|---|---|---|
| `KpiGrid` | < 900 / ≥ 900 | 2 / 6 columns, ruled like a ledger |
| Dashboard lists | < 980 / ≥ 980 | **Needs you** above Risk / side by side; the charts always follow in one column |
| `ChartPanel` | < 640 / 640–959 / ≥ 960 | Compact / medium / wide drawing of the chart; always the full content width |
| `MoneyFlow` | < 640 / ≥ 640 | Two ranked bar lists (money came from, money went to) / Sankey (medium or wide) |
| `SegmentedControl` | any | One row; scrolls sideways when the options do not fit, never wraps |
| `LabelPanel`, `EventInspector` | < 860 / ≥ 860 | Form, then provenance and content / the two side by side; the panel sits below its table |
| `RunWaterfall` | < 600 / ≥ 600 | Name and duration, the bar under them / name, bar and duration in one row |
| `MonthStrip` | < 900 / ≥ 900 | Horizontal scroll with snap (152 px tabs) / six tabs in one row |
| `ResponsiveTable` | < 760 / ≥ 760 | Each row becomes a card (primary cell, amount, status line) / table |
| `ReviewLayout` | < 980 / ≥ 980 | Queue, then the item as its own page / queue beside a sticky fix panel |
| `FixPanel` subject and candidates | < 560 / ≥ 560 | Amount below the name / amount on the right |
| `UsageMeters` | < 560 / ≥ 560 | 1 / 2 columns |
| `PlanCards` | < 620 / 620–899 / ≥ 900 | 1 / 2 / 2 columns, coming-soon features below |
| `FormGrid` | < 480 / ≥ 480 | 1 / 2 columns |
| `EvidenceViewer` | < 600 / < 840 / ≥ 840 | Page opens zoomed to the evidence (magnifier) / page then finding / page beside finding |

### 5.3 Touch, pointer and keyboard

- Hit areas ≥ 44 × 44 px on coarse pointers and on compact screens (buttons, tabs, chips, nav).
- Nothing is reachable only by hover: Sankey bands and tooltips have a tap equivalent, and disabled
  controls show their reason inline.
- Keyboard shortcuts (`j`/`k`, `Enter`, `Esc`, `/` for search, `+`/`-`) are shown on expanded and large
  screens only and never replace a visible control.
- Sticky elements stack in one **dock** (the floating upload button above the bottom navigation, or
  the fix panel's primary action) so they never overlap.
- `env(safe-area-inset-*)` padding on the bottom navigation, the dock and sheets.

### 5.4 Installable web app (P1)

`manifest.webmanifest` (name Kredibel, `display: standalone`, theme colour `#0E5A47`, background
`#F2F4F5`, maskable icons from `design/brand/favicon.svg`). The **share target** accepts images and
PDFs, so a receipt photo can be sent to Kredibel from the phone's share sheet. A service worker caches
the **app shell only**; API responses and documents are never cached on the device.

---

## 6. Signature elements

### 6.1 `ReadingMark`: the provenance rule

Wraps a figure and draws `text-decoration: underline` with style `double`, `dotted` or `wavy` (§2.2),
1 px thick, offset 0.28 em, `text-decoration-skip-ink: none`. Props: `reading` (`AGREED`,
`SINGLE_SOURCE`, `CONFLICT`), `sourceRef?`. It adds visually hidden text ("agreed by two readings")
and, when `sourceRef` is set, becomes a link to the evidence. Used on every figure that comes from
printed values: dashboard and month figures, calculation tables, bank lines. A computed figure
carries `AGREED` only when every input value is agreed. A legend sits under the bank-line table.

### 6.2 `MonthStrip`: months as binder tabs

One tab per month, like the dividers of a ring binder: month name (wide, 22 px) and year; state with
its icon (Reconciled, *n* need you, Reconciling, Collecting); "86% matched by Kredibel" with a meter
and "39 of 45 bank lines"; a dashed rule; the risk badge and its reason in a few words ("Statement
edited"). The top edge is a 4 px rule in the state's colour (brand for reconciled, medium line for
open, high for high, critical for critical); a critical month is tinted from the top. A month with no
statement says "Collecting" and what it holds. The whole tab is one link to the month.

### 6.3 `EvidenceBox`: the lamp

An absolutely positioned box over a page region (normalized bbox × rendered size): 2 px
`evidence.line` outline, 16% `evidence.fill`, radius 3, and a numbered marker (18 px, top right) that
matches the number in the finding's calculation. On first open the lamp sweeps once (§4). On compact
screens the viewer opens **zoomed to the union of the boxes** (a magnifier window 232 px high) with a
**Whole page** button; pinch and the zoom control still work. Without a box: "Exact location not
available (scanned page)" and the page is shown whole.

### 6.4 `MoneyFlow`: where the money went

The dashboard's main chart, grouped the way the workspace's accounting framework groups a
cash-flow statement ([`08`](08-risk-engine.md) §4.1, §5.1). Default view **Flow**, a four-column
Sankey:

1. **Revenue and other money in:** clients, largest first, at most five, then "Other clients" and
   "Cash sales deposited"; other inflow lines (other income, loans and owner) after them.
2. **Account:** one node per bank account, labelled with the bank and masked number.
3. **Activity:** Operating, Investing (only when non-zero), Financing, and Kept, in the activity
   colours of §2.3; the column heading names the framework ("Activity (IFRS)").
4. **Statement line:** Cost of sales, Payroll, Rent and utilities, Repairs and services, Other
   operating expenses, Taxes paid, Finance costs, Loan principal repaid, Owner drawings, in the
   framework's wording (US GAAP: Cost of goods sold, Interest expense, Other SG&A).

Layout from `d3-sankey` with `nodeAlign: justify`, node width 10 (account 16, activity 12), gap 10
(activity 28); we draw the SVG ourselves with the tokens of §2.3.

- Labels sit outside the nodes: name, then the amount in muted tabular figures; activity labels sit
  above their node. The unit (IDR millions) is stated once in the section description.
- Hover or focus on a band raises it (`chart.flow-hover`) and shows a tooltip ("ACB ••4821,
  Operating: Cost of sales, 563.9. 52 bank lines. Click to list"); click or `Enter` opens the **flow
  lines drawer** with those bank lines. Bands are focusable in order.
- One callout under the chart is written by code from facts ("Cost of sales took 41.6% of
  revenue"), and one sentence says what the framework changes ("IFRS: interest paid is a financing
  cash flow…"); it changes with the framework switch.
- Other views in the same panel: **Bars** (statement lines as horizontal bars grouped under their
  activity, with totals), **Table**, and **By client and supplier** (the three-column counterparties
  Sankey: sources → account → who was paid).
- Held possible copies are left out until decided, and the footer says so.
- Below 640 px of panel the flow becomes two ranked bar lists (most revenue came from, most money
  went to, plus Kept).
- Role `img` with a `<title>` and `<desc>` that state the totals; the table is the accessible
  alternative.

The two other dashboard charts follow the same rules: **MonthBars** (money in and out per month with
the net above each pair; view **Net and balance**) and **CashFlowWaterfall** (opening balance,
operating, investing, financing, closing balance, each bar starting where the last one ended, values
signed).

---

## 7. Components (`frontend/src/shared/ui/`)

Built with Radix primitives for behaviour (Dialog, Popover, Tooltip, Tabs, RadioGroup, Select,
Collapsible), `cva` for variants and `tailwind-merge` for class composition, lucide icons. Each
component has a Storybook story per state and size class. The mock class names in
`design/mocks/assets/kit.css` are the component names in kebab case.

**App frame**

| Component | Variants / props | Responsive behaviour |
|---|---|---|
| `AppShell` | `nav`, `topBar`, `dock?` | Compact: column with bottom nav; 600–1199: rail; ≥ 1200: labelled sidebar |
| `Sidebar` / `NavRail` / `BottomNav` | `groups[]`, `active`, `counts` | Same items; the rail shows short labels; neutral counts (totals) only in the sidebar; alert counts everywhere |
| `TopBar` | `title`, `back?`, `crumbs`, `actions` | Compact: mark or back + title + bell; ≥ 600: breadcrumbs, period, search, bell, **Upload** |
| `WorkspaceSwitcher` | `workspace` | Name, type, currency and framework ("Company, IDR, IFRS"); one workspace in P0 |
| `TrialStatus` / `TrialBadge` | `daysLeft`, `usage` | Two-line row in the sidebar foot (days left, a thin pages meter; opens Plan and usage); badge in the top bar below 1200 px |
| `Dock` / `UploadFab` | children | Sticks to the bottom; stacks the floating **Upload** over the bottom nav |
| `Sheet` | `side` (`bottom`, `right`), `size` | Bottom sheet with handle on compact; right sheet 440 px at ≥ 600; focus trap; `Esc` |
| `MoreSheet` | `items[]` | Compact only: the bottom nav's **More** opens the rest of the navigation as a bottom sheet |
| `Drawer` | `size` (`md` 480, `lg` 960, `xl` 1200) | Full screen below 840; URL-addressable for evidence |

**Data and evidence**

| Component | Variants / props | Rules |
|---|---|---|
| `ReadingMark` | `reading`, `sourceRef?` | §6.1 |
| `DataTable` | `columns[]`, `filters[]`, `searchable`, `pageSize` (default 10) | Every list of records (documents, months, bank lines, invoices and receipts, findings, bank accounts): filter chips with counts, search, 10 rows a page with "1 to 10 of 45", sortable columns, keyboard rows; below 760 px the rows become cards. Short summaries on the dashboard (top five) are lists, not tables |
| `MonthStrip` / `MonthTab` | `months[]` | §6.2 |
| `EvidenceBox` | `boxes[] {bbox, index, label}`, `mode` (`page`, `magnifier`) | §6.3 |
| `SankeyChart`, `StatementBars`, `FlowList`, `FlowTable` | `nodes[]`, `links[]`, `view`, `framework`, `hot?` | §6.4 |
| `ChartPanel` | `title`, `description`, `views?`, `wide`, `medium`, `compact`, `foot?` | Full content width; picks the drawing by its own width (§2.3); views switch with a `SegmentedControl` in the head |
| `MonthBars` / `CashFlowWaterfall` | `months[]` / `steps[]`, `framework` | §6.4; the risky month outlined; waterfall values signed |
| `LabelTable` | `labels[]`, `selected?` | Subject with `PageTypeChips`, value, `ConfidenceMeter`, `LabelStatus`, source, extraction link, run, dataset use; cards on compact |
| `LabelPanel` | `label`, `categories[]`, `framework` | AI proposal with confidence and reason, correction field, **Apply to similar lines**, note, **Confirm** / **Save correction**; extraction preview and provenance beside |
| `ConfidenceMeter` | `value` (0–1 or none) | 56 px bar and two decimals; below the task's needs-check threshold in amber, below 0.5 in critical; "no score" when none |
| `LabelStatus` | `status`, `needsCheck` | Needs a check (amber), AI proposed (outline), Verified by a person and Corrected by a person (brand, with a tick) |
| `PageTypeChips` | `pages[] {pageNo, type, confidence}` | `p3 Terms or cover 0.62`; a chip below its threshold is tinted amber |
| `RunWaterfall` / `EventInspector` | `spans[]`, `selected?` / `event` | Spans on one time axis: model calls evidence violet, code slate, workflow and nodes brand at 55%; the inspector shows model, prompt, latency, tokens, span and the captured request and response |
| `KpiGrid` / `Kpi` | `label`, `value`, `unit`, `note`, `meter?`, `attention?` | Ruled grid, no cards; `attention` colours the value (high) |
| `StatusHero` | `sentence {done, ask}`, `reasons[]`, `actions` | The done part in brand, the ask part with a medium highlight under it |
| `MatchChip` / `MatchReason` | `method`, `status`, `reasons[]` | §2.2 match chips; reasons in plain words from codes |
| `CalcTable` | `rows[] {op, label, amount, reading?, marker?}` | Operators in a narrow column; total row sunken; difference row critical |
| `ReadingsTable` | `rows[] {label, aiReader, witness, result}` | Column headers carry the source icons (Gemini, text layer, OCR) |
| `ResponsiveTable` | `columns[] {key, priority}` | Priority 1 cells stay in card mode; others hide |
| `MoneyText` | `money`, `signed?`, `compact?` | `IDR 1,250,000`; compact `IDR 1,355.8 M`; money in green with `+`, money out in ink with `−` |
| `DateText` | `date` | `14 Mar 2026` |
| `CodeText` | — | `type-code` on a sunken tag; never monospace |
| `MiniBars` | `rows[] {label, value}` | The assistant's small chart; values from tool output only |

**Status and feedback**

| Component | Variants / props | Rules |
|---|---|---|
| `Badge` | `neutral`, `brand`, `outline` | Base for the semantic badges |
| `SeverityBadge` / `RiskBadge` | `severity` | Icon + text + colour |
| `VerdictBadge` | `verdict` | Icon + label on screen (§2.2); Not checked dashed |
| `StatusLine` | `state` | Icon + text: Read, Imported, Held, Page 2 of 3, Could not read |
| `KindTile` | `kind` (`dup`, `match`, `doc`) | 36 px tile with the review kind's icon: possible copies amber, matches brand, documents low blue |
| `CitationChip` | `kind` (`fact`, `finding`, `doc`), `label` | Evidence-violet pill with the eye icon |
| `TrialTrack` | `day`, `total` | 30 cells, used ones mint |
| `UsageMeter` | `label`, `used`, `max`, `unit` | Bar + numbers; amber from 80%, critical at 100%; the note says what happens at the limit |
| `ComingSoonBadge` | — | Outline badge; wraps disabled controls and says why |
| `Toast` | `success`, `error`, `info` | Inverse surface; errors stay until dismissed |
| `Skeleton`, `EmptyState` | — | Skeletons mirror the final layout; empty states say what will appear and how |

**Input and actions**

| Component | Variants / props | Rules |
|---|---|---|
| `Button` | `primary`, `secondary`, `ghost`, `quiet`, `inverse`; `sm`, `md`, `lg`, `block`; `loading`; `disabledReason` | 40 px (44 on touch); disabled with a reason stays focusable and explains itself |
| `IconButton` | `label` (required) | 44 px hit area |
| `ChoiceCards` | `options[] {value, label, description, icon}` | Radio cards in a 2-column grid: Myself or A company |
| `CandidateCard` | `title`, `amount`, `why[] {ok, text}`, `fit` | A radio card with reason tags (✓ / ✗) and a fit meter; the picked one has a 2 px brand border |
| `ChipGroup` | `options[] {label, count}`, `multi?` | Filters; scrolls horizontally on compact |
| `SegmentedControl` | `options[] {value, label}`, `value`, `label` | Pill group with `aria-pressed`; one row, scrolls sideways when tight; for views and the framework switch, not for navigation |
| `Field`, `Input`, `Select`, `Textarea` | `hint`, `error`, `optional` | Label above; "(optional)" in the label; 16 px text on compact |
| `Disclosure` | `title`, `summary` | Optional form sections; the summary says what is inside |
| `UploadTray` | `accept`, `maxSize`, `multiple` | Drop area and live rows ([`11`](11-frontend.md) §6.3); on compact **Choose files** and **Photo of a receipt** |
| `SuggestionCard` | `field`, `display`, `confidence`, `basis`, `evidence[]`, `status`, `conflictWith?` | Accept (primary) and Reject (secondary); a conflict shows both values side by side |
| `PlanCard` | `plan`, `current?` | Current: 2 px brand border and "Your plan"; coming soon: dashed, muted, disabled action, no price |
| `MaskedText` | `value` | Never a full account or ID number (`ACB ••4821`); copy disabled |

---

## 8. Content style

- Say what Kredibel **found**, not what "the AI thinks": *"The running balance does not add up on
  14 Mar."* Lead with the consequence, then the evidence, then the next step.
- No alarm words ("fraud!", "fraudster", "fake"). Use *edited*, *does not add up*, *not seen before*,
  *possible copy*. The level is named once ("Critical") and explained.
- Name the money: *"IDR 18,700,000 on 9 Feb fits two invoices"*, not *"Ambiguous match"*.
- Actions keep their name through the flow: **Match with invoice 0003** → toast "Matched"; **Same
  document** → "Kept as a copy"; **Upload** → "Uploaded". Buttons say what happens.
- Duplicates are never "deleted": an exact copy is *"Already uploaded … Not read again and not
  counted"*; a possible copy is *"Held until you decide"*.
- Who did it is always visible: *"Matched by Kredibel"*, *"Matched by Maya on 12 Jul"*, *"Written by
  Gemini. Every figure checked by Kredibel."*
- Money `IDR 1,250,000` (no decimals unless non-zero); compact `IDR 1,355.8 M`; percentages no
  decimals (`86%`) except the dashboard's matched share (`89.6%`). Dates `14 Mar 2026`; months
  `March 2026` in titles and `Mar` in tabs.
- Finding codes appear in `CodeText` next to the human title, never alone.
- Limits are facts with a next step: *"114 pages left. Re-uploaded pages are free."* Never "Upgrade
  now" while paid plans are coming soon.
- Empty states invite an action; errors say what happened and how to fix it, without apologising.
- British spelling (*colour*, *recognised*); every string lives in `locales/en/*.json`.

---

## 9. Brand

<p><img src="assets/mocks/brand-desktop.png" alt="The Kredibel brand page: the mark, construction grid, versions, colours, misuse and uses in the product" width="66%"></p>

- **Idea: a k that has been checked.** The mark is two strokes on a green tile. The **white stem** is
  the document, a column of printed numbers; the **mint tick** is Kredibel reading it a second time
  and agreeing; it grows out of the middle of the stem, so a check is always attached to a source.
  Together they make the k of kredibel.
- **Construction** (64-unit square): tile radius 18; stem 9.5 × 41 at x 14.5, rounded ends; tick of
  the same 9.5 stroke with round caps and join, from 25.5, 34 (its cap overlaps the stem) down to
  35, 44.5 and up to 49, 15.5. Clear space is one stem width on every side.
- **Small sizes:** at 32 px and below use `favicon.svg` (strokes 11, radius 16).
- **Wordmark:** `kredibel` in Archivo 720 at 116% width, lowercase, outlined to paths; the lockup gap
  is a quarter of the tile.
- **Files** in [`design/brand/`](../design/brand/): `kredibel-logo.svg`, `kredibel-logo-on-dark.svg`,
  `kredibel-mark.svg`, `kredibel-mark-on-dark.svg`, `kredibel-mark-mono.svg`,
  `kredibel-wordmark.svg`, `favicon.svg`.
- **In the product:** full logo in the sidebar; the mark in the rail and the compact top bar; the mark
  as the Finance Assistant's avatar.
- **Never:** a red or amber tick, a tick detached from the stem, rotation or stretching, another tile
  colour.
- **Tagline:** *Every number has a source.*
- **Onboarding brand panel:** ink surface with a ledger-paper texture (5% rules every 40 px), the
  tagline, three promises, and three ledger lines showing *read twice*, *matched* and *copy, not
  read*. This is the only decorative texture in the product.
- No stock imagery; the product's own evidence viewer and money flow are the heroes in the README and
  the deck.

Full page: [`design/mocks/brand.html`](../design/mocks/brand.html).

---

## 10. Accessibility checklist (per component PR)

- [ ] Contrast: text ≥ 4.5:1, large text and UI boundaries ≥ 3:1 (token pairs are checked by
      `make tokens`; component states by axe in Storybook).
- [ ] Keyboard: reachable, operable, visible focus ring; dialogs, drawers and sheets trap and restore
      focus; Sankey bands are focusable.
- [ ] Meaning not by colour alone (icon, text or shape present).
- [ ] Icons: `aria-hidden` next to text, or an `aria-label` when alone.
- [ ] Targets ≥ 44 px on touch; nothing hover-only.
- [ ] Works at 200% zoom and at 360 px wide without horizontal page scroll (tables and strips scroll in
      their own box).
- [ ] Charts have a table alternative and a text summary.
- [ ] `prefers-reduced-motion` removes the lamp sweep and slide transitions.
- [ ] Live regions announce upload and reconciliation changes politely.

---

## 11. The mocks

[`design/mocks/`](../design/mocks/index.html) holds static, responsive HTML mocks of the key screens,
built only from `tokens.css` and `assets/kit.css` with synthetic data (the demo workspace of
[`18`](18-synthetic-data.md): Sunrise Coffee Roasters, January to June 2026, scenarios S1 to S4 together). They are the visual reference for the specs and the `/ui-screen`
skill. They are not app code: the app rebuilds the same components in React.

The HTML is generated by `tools/design/mocks/` (one Python function per screen, a shared shell, the
dashboard charts and the icon set), so a change to the shell or a component lands on every screen.
The mocks link to each other, so the folder works as a **clickable prototype** from `dashboard.html`;
`assets/proto.js` adds the few behaviours a static page needs (segmented controls, picking a
candidate, selecting a row, the More sheet) and is not app code.

```
make mocks         python3 tools/design/mocks/build_mocks.py  → design/mocks/*.html and index.html
make mock-shots    tools/design/shoot_mocks.py at 390, 834, 1440 px → docs/assets/mocks/*.png
```

| Mock | Shows | Spec |
|---|---|---|
| `onboarding.html` | Myself or a company, the trial terms, the brand panel | 013 |
| `dashboard.html` | Status sentence, figures, Needs you, Risk, then full-width charts with the IFRS / US GAAP switch: money flow (Flow, Bars, Table, By client and supplier), money in and out by month, cash-flow statement; months as binder tabs | 010 |
| `documents.html` | Upload tray with an exact copy, a held copy, a page being read and a new ledger layout; the library | 003, 006 |
| `document.html` | One read statement: page viewer (pages, zoom, the lamp) beside the figures and the transactions with reading marks, filters and pages | 003, 005, 006 |
| `month.html` | March 2026: figures, the critical explanation with citations and next steps, bank lines with matches | 007, 008 |
| `review.html` | The queue by month and the fix panel for a bank line that fits two invoices | 009 |
| `evidence-viewer.html` | The lamp, calculation, two readings; magnifier on compact | 005, 008 |
| `assistant.html` | Finance Assistant answer with a citation chip, a small chart, and what is remembered (P1) | 011 |
| `plan-usage.html` | Trial track, usage meters, plan cards, coming-soon features | 013 |
| `risk.html` | Findings grouped by month with severity, code, where and status | 008 |
| `clients.html` | Clients and suppliers with shares; a supplier paid to a new account and one never paid are flagged | 014 |
| `labels.html` | Labels to check: per-page types, confidence, status, extraction files, runs, dataset use, and the label panel (P1) | 016 |
| `runs.html` | Runs, a span waterfall and the inspector for one model call (P1, owner only) | 017 |
| `samples/*.md` | Page extraction Markdown the Labels page links to | 016 |
| `brand.html` | The logo idea, construction, versions, colours, misuse, uses | — |
