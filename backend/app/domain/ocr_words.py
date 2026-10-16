"""OCR tokens into words (spec 022 phase B, docs/07 §5.3). Document AI returns punctuation as its
own small token and a photo's line can tilt; joined and levelled, the words look to the verifier
and the layout like a PDF text layer's."""

from dataclasses import dataclass
from statistics import median

from .verify import Word

JOIN_GAP = 0.01  # of the page width: tokens with no break between them are also this close


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
