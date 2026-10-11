"""The logo and brand page (design/mocks/brand.html). Explains the k-and-tick mark, its construction,
clear space, sizes, colours, variants, misuse and where it appears in the product."""

from icons import icon

BRAND = "../brand"
GREEN, MINT, WHITE, INK, PAPER = "#0E5A47", "#9FE0C6", "#FFFFFF", "#16212B", "#F2F4F5"


def mark_svg(size: int, tick: str = MINT, tile: str = GREEN, stem: str = WHITE, extra: str = "",
             transform: str = "", detached: bool = False) -> str:
    check = "M25.5 34 L35 44.5 L49 15.5" if not detached else "M33 38 L41 47 L54 20"
    return (f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" aria-hidden="true"{extra}>'
            f'<g transform="{transform}"><rect width="64" height="64" rx="18" fill="{tile}"/>'
            f'<path d="{check}" fill="none" stroke="{tick}" stroke-width="9.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<rect x="14.5" y="11.5" width="9.5" height="41" rx="4.75" fill="{stem}"/></g></svg>')


def construction_svg() -> str:
    """The mark on its 64-unit grid with the clear space, the stem, the tick's centre line and its three points."""
    grid = "".join(f'<line x1="{v}" y1="0" x2="{v}" y2="64"/><line x1="0" y1="{v}" x2="64" y2="{v}"/>' for v in range(8, 64, 8))
    pts = [(25.5, 34), (35, 44.5), (49, 15.5)]
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.3"/>' for x, y in pts)
    return f"""<svg class="construct" viewBox="-16 -16 96 96" role="img" aria-labelledby="c-t c-d">
<title id="c-t">How the mark is built</title>
<desc id="c-d">A 64-unit rounded square. A white stem 9.5 units wide and 41 tall stands at x 14.5. A mint tick of the same stroke width starts inside the stem at the middle, drops to its lowest point at 35, 44.5 and rises to 49, 15.5. The clear space around the tile is one stem width.</desc>
<rect class="clear" x="-9.5" y="-9.5" width="83" height="83" rx="22"/>
<rect width="64" height="64" rx="18" fill="{GREEN}"/>
<g class="grid">{grid}</g>
<path d="M25.5 34 L35 44.5 L49 15.5" fill="none" stroke="{MINT}" stroke-width="9.5" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="14.5" y="11.5" width="9.5" height="41" rx="4.75" fill="{WHITE}"/>
<path class="spine" d="M25.5 34 L35 44.5 L49 15.5"/>
<line class="spine" x1="19.25" y1="11.5" x2="19.25" y2="52.5"/>
<g class="pts">{dots}</g>
<g class="dim">
  <g class="on-tile"><line x1="14.5" y1="58.5" x2="24" y2="58.5"/><line x1="14.5" y1="57" x2="14.5" y2="60"/><line x1="24" y1="57" x2="24" y2="60"/></g>
  <text x="19.25" y="70" text-anchor="middle">stem 9.5</text>
  <line x1="-9.5" y1="32" x2="0" y2="32"/><text x="-4.75" y="29" text-anchor="middle">9.5</text>
  <line class="lead" x1="49" y1="15.5" x2="49" y2="-9.5"/><text x="49" y="-11.5" text-anchor="middle">49, 15.5</text>
  <line class="lead" x1="35" y1="44.5" x2="35" y2="66.5"/><text x="35" y="70" text-anchor="start" dx="2">35, 44.5</text>
  <text x="66" y="4" text-anchor="start">r 18</text>
</g>
</svg>"""


def brand_body() -> str:
    idea = f"""
<section class="brand-hero" aria-labelledby="b-h">
  <div class="brand-hero-mark">{mark_svg(232)}</div>
  <div class="brand-hero-text">
    <img src="{BRAND}/kredibel-logo.svg" alt="Kredibel" height="36"/>
    <h1 class="type-title" id="b-h">A k that has been checked</h1>
    <p class="lead">The mark is two strokes. The white stem is the document: a column of printed numbers.
    The mint tick is Kredibel reading it a second time and agreeing. Together they make the k of kredibel.</p>
    <ul class="brand-reads">
      <li><span class="sw stem"></span><span><strong>The stem is what was printed.</strong> Upright, plain, the same width all the way down, like a column in a statement.</span></li>
      <li><span class="sw tick"></span><span><strong>The tick is the check.</strong> It grows out of the middle of the stem, so the check is always attached to a source.</span></li>
      <li><span class="sw tile"></span><span><strong>The green tile is the ledger.</strong> A rounded square that holds both, and the colour of every primary action.</span></li>
    </ul>
  </div>
</section>"""

    build = f"""
<section class="brand-sec" aria-labelledby="b-build">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-build">Construction</h2>
  <p>Drawn on a 64-unit square. Every measure comes from the stem, so the mark scales without drift.</p></div>
  <div class="brand-build">
    <figure class="brand-figure">{construction_svg()}</figure>
    <dl class="brand-specs">
      <div><dt>Tile</dt><dd>64 × 64, corner radius 18 (28%). Ledger green.</dd></div>
      <div><dt>Stem</dt><dd>9.5 wide, 41 tall, at 14.5 from the left, centred vertically. Fully rounded ends.</dd></div>
      <div><dt>Tick</dt><dd>Same 9.5 stroke, round caps and join. Starts at 25.5, 34 so its cap overlaps the stem; lowest point 35, 44.5; ends at 49, 15.5, higher than the stem.</dd></div>
      <div><dt>Clear space</dt><dd>One stem width (9.5 units, about 15% of the tile) on every side. Nothing else enters it.</dd></div>
      <div><dt>Small sizes</dt><dd>At 32 px and below use <code class="code-tag">favicon.svg</code>: the stem and tick are 11 wide and the radius 16, so they stay open at 16 px.</dd></div>
      <div><dt>Lockup</dt><dd>Mark, then a gap of a quarter tile, then the wordmark <em>kredibel</em> in Archivo 720 at 116% width, lowercase, outlined. Cap height lines up with the top of the stem.</dd></div>
    </dl>
  </div>
</section>"""

    variants = f"""
<section class="brand-sec" aria-labelledby="b-var">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-var">Versions</h2>
  <p>Files in <code class="code-tag">design/brand/</code>. Use the SVGs; never redraw the mark.</p></div>
  <ul class="brand-variants">
    <li><div class="plate light"><img src="{BRAND}/kredibel-logo.svg" alt="Kredibel logo on a light surface" height="48"/></div><p><strong>Logo</strong><code class="code-tag">kredibel-logo.svg</code>Sidebar, README, sign-in, documents.</p></li>
    <li><div class="plate dark"><img src="{BRAND}/kredibel-logo-on-dark.svg" alt="Kredibel logo on a dark surface" height="48"/></div><p><strong>Logo on dark</strong><code class="code-tag">kredibel-logo-on-dark.svg</code>Onboarding panel, slides, dark mode.</p></li>
    <li><div class="plate light"><img src="{BRAND}/kredibel-mark.svg" alt="Kredibel mark" height="64"/><img src="{BRAND}/kredibel-mark-mono.svg" alt="Kredibel mark in one colour" height="64"/></div><p><strong>Mark and one-colour mark</strong><code class="code-tag">kredibel-mark.svg</code>Rail, compact top bar, assistant avatar. One colour for print and stamps.</p></li>
    <li><div class="plate light sizes"><img src="{BRAND}/favicon.svg" alt="" height="64"/><img src="{BRAND}/favicon.svg" alt="" height="32"/><img src="{BRAND}/favicon.svg" alt="Favicon at 64, 32 and 16 pixels" height="16"/></div><p><strong>Favicon and app icon</strong><code class="code-tag">favicon.svg</code>Browser tab and installed web app; heavier strokes for small sizes.</p></li>
  </ul>
</section>"""

    colours = f"""
<section class="brand-sec" aria-labelledby="b-col">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-col">Colours</h2>
  <p>Four colours carry the brand. Severity colours are for findings only and never touch the mark.</p></div>
  <ul class="brand-swatches">
    <li><span class="chip-c green"></span><strong>Ledger green</strong><code class="code-tag">brand.default {GREEN}</code><span>The tile, primary buttons, reconciled months.</span></li>
    <li><span class="chip-c mint"></span><strong>Check mint</strong><code class="code-tag">brand.accent {MINT}</code><span>The tick and money kept. Means checked, nothing else.</span></li>
    <li><span class="chip-c ink"></span><strong>Ink</strong><code class="code-tag">bg.inverse {INK}</code><span>Text, the onboarding panel, tooltips.</span></li>
    <li><span class="chip-c paper"></span><strong>Paper</strong><code class="code-tag">bg.canvas {PAPER}</code><span>The page behind every panel.</span></li>
  </ul>
</section>"""

    donts = f"""
<section class="brand-sec" aria-labelledby="b-dont">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-dont">Keep the meaning</h2>
  <p>The tick says a number was checked. Anything that weakens that is off-brand.</p></div>
  <ul class="brand-donts">
    <li><div class="plate light">{mark_svg(88, tick="#C0362C")}</div><p>{icon("x", "icon icon-sm")}No red or amber tick. A warning is never shown with the mark.</p></li>
    <li><div class="plate light">{mark_svg(88, detached=True)}</div><p>{icon("x", "icon icon-sm")}No floating tick. It always grows out of the stem.</p></li>
    <li><div class="plate light">{mark_svg(88, transform="translate(32 32) rotate(-12) scale(0.84) translate(-32 -32)")}</div><p>{icon("x", "icon icon-sm")}No rotating, stretching, outlines or shadows.</p></li>
    <li><div class="plate light">{mark_svg(88, tile="#2B6CB0")}</div><p>{icon("x", "icon icon-sm")}No other tile colours. Partners get a lockup, not a recolour.</p></li>
  </ul>
</section>"""

    product = f"""
<section class="brand-sec" aria-labelledby="b-use">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-use">In the product</h2>
  <p>The mark appears in three places, always at one of three sizes: 40, 32 or 24 px.</p></div>
  <ul class="brand-uses">
    <li><div class="use-plate"><div class="use-side"><img src="{BRAND}/kredibel-logo.svg" alt="" height="34"/><span class="use-nav is-on">{icon("dashboard", "icon icon-sm")}Dashboard</span><span class="use-nav">{icon("files", "icon icon-sm")}Documents</span></div></div><p><strong>Sidebar, 1200 px and up.</strong> Full logo, 34 px high, top left. The rail below 1200 px shows the mark alone.</p></li>
    <li><div class="use-plate"><div class="use-top"><img src="{BRAND}/kredibel-mark.svg" alt="" height="32"/><span>Dashboard</span>{icon("bell")}</div></div><p><strong>Phone top bar.</strong> The mark at 32 px stands in for the logo next to the screen title.</p></li>
    <li><div class="use-plate"><div class="use-chat"><img src="{BRAND}/kredibel-mark.svg" alt="" height="24"/><span class="use-bubble">You paid Green Valley Farms <b>IDR 56,050,000</b> in March.</span></div></div><p><strong>Assistant answers.</strong> The mark is the assistant's avatar: answers are Kredibel checking your books, not a person.</p></li>
  </ul>
</section>"""

    voice = """
<section class="brand-sec brand-voice" aria-labelledby="b-voice">
  <div class="brand-sec-head"><h2 class="type-h2" id="b-voice">Tagline and voice</h2></div>
  <p class="brand-tagline">Every number has a source.</p>
  <div class="brand-voice-cols">
    <div><h3>Say</h3><ul><li>The running balance does not add up on 14 Mar.</li><li>Held until you decide.</li><li>Matched by Kredibel. Matched by you.</li></ul></div>
    <div><h3>Don't say</h3><ul><li>Our AI detected fraud!</li><li>Duplicate deleted.</li><li>Upgrade now to unlock insights.</li></ul></div>
  </div>
</section>"""

    return f"""<div class="viewport"><main class="brand-page">
  <nav class="crumbs brand-crumbs" aria-label="Breadcrumb"><a href="index.html">Screen mocks</a>{icon("chevron-right")}<span aria-current="page">Logo and brand</span></nav>
  {idea}{build}{variants}{colours}{donts}{product}{voice}
</main></div>"""
