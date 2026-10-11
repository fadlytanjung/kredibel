#!/usr/bin/env python3
"""Screenshot the HTML mocks in design/mocks/ at the three reference widths.

Writes docs/assets/mocks/<mock>-<mobile|tablet|desktop>.png (PNG8, so the docs stay small).
The same widths are used by the frontend visual-regression tests (docs/15 §2.6).

Usage (Playwright and Pillow are not project dependencies, so run them ad hoc):
  uv run --with playwright --with pillow python tools/design/shoot_mocks.py            # all mocks
  uv run --with playwright --with pillow python tools/design/shoot_mocks.py dashboard review
First time only: uv run --with playwright playwright install chromium
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
MOCKS = ROOT / "design" / "mocks"
OUT = ROOT / "docs" / "assets" / "mocks"

# name: (width, height, device scale, full page)
SIZES = {
    "mobile": (390, 844, 2, False),     # first screen, as a phone shows it
    "tablet": (834, 1112, 1, False),
    "desktop": (1440, 900, 1, True),
}
# Mocks whose desktop view is a fixed overlay (the drawer scrolls inside itself), so no full page.
FIXED_DESKTOP = {"evidence-viewer"}


def quantize(path: Path) -> None:
    im = Image.open(path).convert("RGB")
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def main(only: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    mocks = sorted(p.stem for p in MOCKS.glob("*.html") if p.stem != "index")
    if only:
        mocks = [m for m in mocks if m in only]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for mock in mocks:
            for kind, (w, h, scale, full) in SIZES.items():
                if kind == "desktop" and mock in FIXED_DESKTOP:
                    full = False
                ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=scale,
                                          reduced_motion="reduce")
                page = ctx.new_page()
                page.goto((MOCKS / f"{mock}.html").as_uri())
                page.wait_for_load_state("networkidle")
                path = OUT / f"{mock}-{kind}.png"
                page.screenshot(path=str(path), full_page=full)
                quantize(path)
                print("wrote", path.relative_to(ROOT))
                ctx.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
