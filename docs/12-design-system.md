# 12 — Design System

> **Direction: "the ledger and the magnifier."** Paper-calm surfaces, ink-dark text, one deep teal
> for trust, and a strict, colour-blind-safe severity scale for anything forensic. Numbers are the
> heroes: tabular, right-aligned, never decorative.

---

## 1. Foundations

### 1.1 Colour tokens

Defined once in `frontend/src/app/styles/theme.css` as CSS variables and exposed to Tailwind v4 via
`@theme`. Components use tokens, never raw hex.

| Token | Hex | Use |
|---|---|---|
| `--color-bg` | `#F7F8F6` | App background ("paper") |
| `--color-surface` | `#FFFFFF` | Cards, panels, tables |
| `--color-surface-muted` | `#F0F2EF` | Table headers, hovered rows, wells |
| `--color-border` | `#DDE1DC` | Dividers, inputs |
| `--color-border-strong` | `#B8BFB9` | Focused inputs, active tabs |
| `--color-text` | `#14201C` | Primary text ("ink") |
| `--color-text-muted` | `#55625D` | Secondary text, labels |
| `--color-text-subtle` | `#7A8681` | Placeholders, captions |
| `--color-brand` | `#0F5E56` | Primary actions, links, active states |
| `--color-brand-hover` | `#0B4B45` | Hover/pressed |
| `--color-brand-soft` | `#E3F1EE` | Selected rows, brand badges |
| `--color-focus` | `#1F7A70` | 2 px focus ring, 2 px offset |

**Severity scale** (text colour on soft background; each pair ≥ 4.5:1):

| Severity | Text / icon | Soft bg | Icon (lucide) |
|---|---|---|---|
| Critical | `#B42318` | `#FEE4E2` | `octagon-alert` |
| High | `#C4320A` | `#FFEAD5` | `triangle-alert` |
| Medium | `#93370D` | `#FEF0C7` | `circle-alert` |
| Low | `#175CD3` | `#D1E9FF` | `info` |
| Info | `#475467` | `#F2F4F7` | `circle-dot` |

**Integrity verdicts:**

| Verdict | Colour | Soft bg | Icon | Extra |
|---|---|---|---|---|
| Clean | `#067647` | `#DCFAE6` | `shield-check` | |
| Suspicious | `#93370D` | `#FEF0C7` | `shield-alert` | |
| Tampered | `#B42318` | `#FEE4E2` | `shield-x` | |
| Unverifiable | `#475467` | `#F2F4F7` | `shield-question` | dashed border |

**Grades:** A `#067647` · B `#2E7D5B` · C `#93370D` · D `#C4320A` · E `#B42318`.

**Charts** (categorical, colour-blind-safe, max 5 series per chart):

| Series | Colour |
|---|---|
| Operating inflow | `#0F766E` |
| Operating outflow | `#94A3B8` |
| Net / CADS line | `#14201C` |
| Average daily balance (line, dashed) | `#6D28D9` |
| Negative-balance markers | `#B42318` |

Dark mode is P2; tokens are structured so it is a second variable set, not new components.

### 1.2 Typography

| Role | Family | Notes |
|---|---|---|
| UI text | **IBM Plex Sans** (400, 500, 600) | Self-hosted via `@fontsource/ibm-plex-sans` |
| Codes, IDs, raw extracted values | **IBM Plex Mono** (400, 500) | Finding codes (`A01_…`), `KRD-…`, "as printed" values |
| Numbers | Plex Sans with `font-variant-numeric: tabular-nums lining-nums` | Utility class `num` |

| Style | Size / line height | Weight |
|---|---|---|
| `display` | 30 / 36 | 600 |
| `h1` | 24 / 32 | 600 |
| `h2` | 20 / 28 | 600 |
| `h3` | 16 / 24 | 600 |
| `body` | 14 / 20 | 400 |
| `body-strong` | 14 / 20 | 500 |
| `caption` | 12 / 16 | 400 |
| `metric` | 28 / 32 | 600, tabular |

Body text is 14 px: this is a dense, professional tool. Sentence case everywhere.

### 1.3 Space, shape, depth, motion

- Spacing scale: 4 px base: 4, 8, 12, 16, 20, 24, 32, 40, 48.
- Radius: `sm` 4 px (badges, inputs), `md` 8 px (cards, buttons), `lg` 12 px (drawers, dialogs).
- Elevation: `shadow-sm` for cards; `shadow-lg` for drawers and popovers only. Prefer borders to shadows.
- Motion: 150 ms ease-out for hovers and toggles; 250 ms for drawers; pipeline ticks fade + 4 px
  rise. Everything respects `prefers-reduced-motion`.
- Layout: max content width 1440 px; workspace grid `minmax(0,1fr) 360px` at ≥1280 px.

---

## 2. Tailwind v4 theme (excerpt)

```css
/* frontend/src/app/styles/theme.css */
@import "tailwindcss";

@theme {
  --color-bg: #F7F8F6;
  --color-surface: #FFFFFF;
  --color-surface-muted: #F0F2EF;
  --color-border: #DDE1DC;
  --color-text: #14201C;
  --color-text-muted: #55625D;
  --color-brand: #0F5E56;
  --color-brand-hover: #0B4B45;
  --color-brand-soft: #E3F1EE;

  --color-sev-critical: #B42318;  --color-sev-critical-soft: #FEE4E2;
  --color-sev-high: #C4320A;      --color-sev-high-soft: #FFEAD5;
  --color-sev-medium: #93370D;    --color-sev-medium-soft: #FEF0C7;
  --color-sev-low: #175CD3;       --color-sev-low-soft: #D1E9FF;
  --color-sev-info: #475467;      --color-sev-info-soft: #F2F4F7;
  --color-ok: #067647;            --color-ok-soft: #DCFAE6;

  --font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}

@utility num {
  font-variant-numeric: tabular-nums lining-nums;
}
```

---

## 3. Components (`frontend/src/shared/ui/`)

| Component | Variants / props | Rules |
|---|---|---|
| `Button` | `primary`, `secondary`, `ghost`, `danger`; `sm`, `md`; `loading`; `disabledReason` | A disabled button with `disabledReason` shows it in a tooltip and is still focusable |
| `Badge` | `neutral`, `brand` | Base for the semantic badges below |
| `SeverityBadge` | `severity` | Icon + text + colour; never colour alone |
| `VerdictBadge` | `verdict` | Icon + text; Unverifiable uses a dashed border |
| `GradeBadge` | `grade`, `score?` | Square, 24 px, mono letter |
| `StatusBadge` | `CaseStatus` | Neutral palette except `FAILED` (critical) and `APPROVED`/`DECLINED` (ok / critical outline) |
| `Card` | `title`, `actions`, `footer` | 16 px padding, border, `radius-md` |
| `StatTile` | `label`, `value`, `unit`, `hint`, `trend?`, `status?` | Value uses `metric` style; "?" popover for the formula |
| `Tabs` | counts in labels | Keyboard arrows; URL-synced |
| `DataTable` | sticky header, sortable columns, row click, empty/loading | Numbers right-aligned with `num` |
| `MoneyText` | `money`, `signed?`, `compact?` | `IDR 1,250,000`; negative in `--color-sev-critical` with a minus sign |
| `DateText` | `date` | `14 Mar 2026` |
| `CodeText` | — | Mono, `surface-muted` background, 2 px radius |
| `Drawer` | `side`, `size` (`md` 480, `lg` 960, `xl` 1200) | Focus trap, `Esc` closes, URL-addressable when used for evidence |
| `Dialog` | `confirm`, `form` | Destructive confirms name the consequence |
| `Toast` | `success`, `error`, `info` | 5 s; errors persist until dismissed |
| `Tooltip`, `Popover` | — | |
| `Skeleton` | shapes | Mirrors final layout |
| `EmptyState` | `title`, `body`, `action` | Says what will appear here and how |
| `Dropzone` | `accept`, `maxSize`, `multiple` | Per-file progress rows |
| `Stepper` | `steps[] {label, status}` | Used by PipelineProgress; statuses pending/running/done/skipped/failed |
| `CitationChip` | `kind` (`fact`, `finding`, `doc`), `label` | Small, inline, brand-soft; finding chips take severity colour |
| `BBoxOverlay` | `boxes[] {bbox, severity, label, index}` | 2 px border + 12% fill in severity colour, numbered marker |
| `Gauge` | `score`, `grade` | Semi-circle, 0–100, grade colour |
| `SegmentedControl` | `options[]`, `value` | Used for **Individual \| Company**; arrow keys move; each option has an icon and text |
| `Wizard` | `steps[] {label, status}`, `current` | Three steps for New case; Back keeps entered data; step titles are links once visited |
| `RepeatableFieldset` | `items[]`, `onAdd`, `onRemove`, `max` | Bank accounts and people in onboarding; empty state "Add an account or let Kredibel suggest one" |
| `MaskedText` | `value` (e.g. `••••4821`) | Never renders a full account number; copy is disabled |
| `ApplicantTypeIcon` | `type` | Person or building icon plus an accessible label |
| `ReadingBadge` | `kind` (`DIGITAL`, `SCANNED`, `MIXED`) | Neutral palette; tooltip explains the witness used |
| `ConfidenceBadge` | `HIGH`, `MEDIUM`, `LOW` | Dots plus text (●●● High); never colour alone |
| `SuggestionCard` | `field`, `display`, `confidence`, `basis`, `evidence[]`, `status`, `conflictWith?` | Accept (primary) and Reject (ghost); conflict layout shows "Profile says" / "Documents say" side by side |
| `ComingSoonBadge` | — | Neutral outline badge "Coming soon"; wraps disabled controls and explains why in a tooltip |
| `PlanCard` | `plan`, `current?` | Current plan has a brand border; coming-soon cards are muted with disabled actions and no price |
| `UsageMeter` | `label`, `used`, `max`, `unit` | Bar + numbers; amber from 80%, critical at 100%; text says what happens at the limit |
| `TrialBadge` | `daysLeft`, `status` | In the app header; "Free trial · 23 days left", "Trial ended" |

---

## 4. Content style

- Say what Kredibel **found**, not what "the AI thinks": *"The running balance does not add up on
  14 Mar."*
- Lead with the consequence, then the evidence: *"Revenue looks overstated: 5 of 10 invoices have no
  matching payment."*
- No alarm words ("fraudster", "fake") in UI copy. Use *tampered*, *inconsistent*, *unverified*.
- Money `IDR 1,250,000` (no decimals in UI unless non-zero); ratios two decimals (`1.42×`);
  percentages no decimals (`64%`).
- Dates `14 Mar 2026`; months `Mar 2026`.
- Finding codes always shown in `CodeText` next to the human title.
- Suggestions say where a value came from, not that the AI "believes" it: *"Printed as the issuer's
  tax ID on 10 invoices."*
- Limits are stated as facts with a next step: *"12 of 300 pages left this month. Pages already read
  are free to re-run."* Never "Upgrade now" while paid plans are coming soon.
- One English variant everywhere: British spelling, like these docs (*colour*, *behaviour*). Every
  string lives in `locales/en/*.json`.

---

## 5. Brand

- Wordmark: **kredibel** in Plex Sans 600, lowercase, brand teal; the dot of the *i* replaced by a small
  check-square. Favicon: white "k" on a teal rounded square.
- Tagline under the wordmark on the login page: *Every number has a source.*
- Login page: split layout. Left: wordmark, tagline, three one-line value props. Right: sign-in card.
- No stock imagery. The product's own evidence viewer screenshot is the hero in the README and deck.

---

## 6. Accessibility checklist (per component PR)

- [ ] Contrast ≥ 4.5:1 for text, ≥ 3:1 for UI boundaries (checked with axe in component tests).
- [ ] Keyboard reachable and operable; visible focus.
- [ ] Meaning not by colour alone.
- [ ] Icons have `aria-label` or are `aria-hidden` next to text.
- [ ] Live regions announce pipeline stage changes politely (`aria-live="polite"`).
