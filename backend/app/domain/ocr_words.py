"""OCR tokens into words (spec 022 phase B, docs/07 §5.3). Document AI returns punctuation as its
own small token, and a photo of a page is often turned a little; straightened, joined and levelled,
the words look to the verifier and the layout like a PDF text layer's."""

from dataclasses import dataclass, replace
from statistics import median

from .verify import Word

JOIN_GAP = 0.01  # of the page width: tokens with no break between them are also this close
TILT_SPAN = 0.12  # of the page width: OCR lines at least this wide measure the page's tilt
MIN_TILT = 0.002  # a smaller slope (about 0.1 degree) is left as printed


@dataclass(frozen=True)
class OcrToken:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    line: int  # the OCR line it belongs to
    space_after: bool  # the OCR saw a space or a line break after it


def ocr_words(tokens: list[OcrToken]) -> list[Word]:
    """Tokens of one line with no break between them become one word ("parcel" + "," is
    "parcel,"); every word takes its line's median top and bottom, so a tilted line stays one
    line and a stray tall token cannot stretch it."""
    lines: dict[int, list[OcrToken]] = {}
    for token in tokens:
        lines.setdefault(token.line, []).append(token)
    slope = _tilt(lines)
    if abs(slope) >= MIN_TILT:
        lines = {n: [_straightened(t, slope) for t in line] for n, line in lines.items()}
    out: list[Word] = []
    for line in lines.values():
        top = median(t.top for t in line)
        bottom = median(t.bottom for t in line)
        joined: list[tuple[str, float, float]] = []
        previous: OcrToken | None = None
        for token in line:
            if (
                previous is not None
                and not previous.space_after
                and joined
                and token.x0 - joined[-1][2] <= JOIN_GAP
            ):
                text, x0, x1 = joined[-1]
                joined[-1] = (text + token.text, min(x0, token.x0), max(x1, token.x1))
            else:
                joined.append((token.text, token.x0, token.x1))
            previous = token
        out += [Word(text, x0, x1, top, bottom) for text, x0, x1 in joined]
    return out


def _tilt(lines: dict[int, list[OcrToken]]) -> float:
    """The page's slope (dy/dx), the median over its wide OCR lines: on a turned photo a row's
    amounts on the right sit higher or lower than its date on the left, and the OCR often puts
    the columns on separate lines, so they would pair with the wrong row."""
    slopes: list[float] = []
    for line in lines.values():
        xs = [(t.x0 + t.x1) / 2 for t in line]
        if len(line) < 2 or max(xs) - min(xs) < TILT_SPAN:
            continue
        ys = [(t.top + t.bottom) / 2 for t in line]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        spread = sum((x - mx) ** 2 for x in xs)
        slopes.append(sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / spread)
    return median(slopes) if slopes else 0.0


def _straightened(token: OcrToken, slope: float) -> OcrToken:
    shift = slope * ((token.x0 + token.x1) / 2 - 0.5)
    return replace(token, top=token.top - shift, bottom=token.bottom - shift)
