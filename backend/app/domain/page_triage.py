"""Page triage domain logic (AC-003-4, docs/07 §3.1).

Deterministic triage of rendered document pages:
- USABLE: >= 40 chars & >= 80% printable/decodable (no cid glyphs) -> witness TEXT_LAYER
- UNUSABLE: characters exist but fail the threshold -> witness OCR
- NONE: no characters (scan or image) -> witness OCR
- blank: >= 99.5% near-white and 0 characters -> blank = True
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_CID_PATTERN = re.compile(r"\(cid:\d+\)")
_BLANK_NEAR_WHITE_THRESHOLD = 0.995
_MIN_USABLE_CHAR_COUNT = 40
_MIN_USABLE_PRINTABLE_RATIO = 0.80


class TextLayerStatus(StrEnum):
    USABLE = "USABLE"
    UNUSABLE = "UNUSABLE"
    NONE = "NONE"


class WitnessType(StrEnum):
    TEXT_LAYER = "TEXT_LAYER"
    OCR = "OCR"


@dataclass(frozen=True)
class PageTriageResult:
    text_layer: TextLayerStatus
    witness: WitnessType
    blank: bool
    char_count: int = 0
    printable_ratio: float = 0.0


def compute_near_white_ratio(image: Any) -> float:
    """Compute the fraction of pixels that are near-white (brightness >= 250 / 255).

    Accepts any PIL Image. Uses an 8-bit luminance histogram for O(1) memory overhead.
    """
    if hasattr(image, "convert") and hasattr(image, "histogram"):
        gray = image.convert("L")
        hist = gray.histogram()
        total_pixels = sum(hist)
        if total_pixels == 0:
            return 0.0
        near_white_pixels = sum(hist[250:])
        return near_white_pixels / total_pixels
    return 0.0


def _analyze_characters(
    text: str | None = None,
    chars: Sequence[str] | None = None,
) -> tuple[int, float]:
    """Analyze characters for count and decodable printable ratio."""
    if chars is not None:
        total = len(chars)
        if total == 0:
            return 0, 0.0
        printable = 0
        for ch in chars:
            if _CID_PATTERN.search(ch):
                continue
            if ch.isprintable() or ch in "\r\n\t ":
                printable += 1
        return total, printable / total

    if text is not None and text:
        cid_matches = _CID_PATTERN.findall(text)
        cid_count = len(cid_matches)
        text_without_cid = _CID_PATTERN.sub("", text)
        printable = sum(
            1 for ch in text_without_cid if ch.isprintable() or ch in "\r\n\t "
        )
        total = cid_count + len(text_without_cid)
        if total == 0:
            return 0, 0.0
        return total, printable / total

    return 0, 0.0


def triage_page(
    text: str | None = None,
    chars: Sequence[str] | None = None,
    near_white_ratio: float | None = None,
    image: Any | None = None,
) -> PageTriageResult:
    """Triage a single page's text layer and blank status.

    Normative rules from docs/07 §3.1:
    - >= 40 chars & >= 80% printable/decodable (no cid) -> USABLE (witness TEXT_LAYER)
    - Characters exist but fail the threshold -> UNUSABLE (witness OCR)
    - No characters -> NONE (witness OCR)
    - >= 99.5% near-white and 0 characters -> blank = True
    """
    char_count, printable_ratio = _analyze_characters(text=text, chars=chars)

    if image is not None and near_white_ratio is None:
        near_white_ratio = compute_near_white_ratio(image)

    # Determine text layer status and witness
    if char_count == 0:
        text_layer = TextLayerStatus.NONE
        witness = WitnessType.OCR
    elif (
        char_count >= _MIN_USABLE_CHAR_COUNT
        and printable_ratio >= _MIN_USABLE_PRINTABLE_RATIO
    ):
        text_layer = TextLayerStatus.USABLE
        witness = WitnessType.TEXT_LAYER
    else:
        text_layer = TextLayerStatus.UNUSABLE
        witness = WitnessType.OCR

    # Determine blank status
    blank = (
        char_count == 0
        and near_white_ratio is not None
        and near_white_ratio >= _BLANK_NEAR_WHITE_THRESHOLD
    )

    return PageTriageResult(
        text_layer=text_layer,
        witness=witness,
        blank=blank,
        char_count=char_count,
        printable_ratio=printable_ratio,
    )
