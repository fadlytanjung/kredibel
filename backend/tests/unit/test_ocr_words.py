"""OCR tokens into words (spec 022 phase B): punctuation joins its word, a tilted line is levelled,
and tokens apart stay apart. Synthetic data only."""

from app.domain.ocr_words import OcrToken, ocr_words
from app.domain.verify import check_items, check_value


def test_a_token_with_no_break_after_it_joins_the_next_one():
    tokens = [
        OcrToken("Express", 0.17, 0.30, 0.447, 0.477, line=5, space_after=True),
        OcrToken("parcel", 0.32, 0.43, 0.452, 0.481, line=5, space_after=False),
        OcrToken(",", 0.43, 0.44, 0.470, 0.485, line=5, space_after=True),
        OcrToken("Jakarta", 0.46, 0.60, 0.450, 0.480, line=5, space_after=True),
        OcrToken("CFS", 0.60, 0.66, 0.30, 0.32, line=2, space_after=False),
        OcrToken("-", 0.66, 0.67, 0.31, 0.312, line=2, space_after=False),
        OcrToken("0602-587", 0.67, 0.80, 0.30, 0.32, line=2, space_after=True),
    ]
    words = ocr_words(tokens)
    assert [w.text for w in words] == ["Express", "parcel,", "Jakarta", "CFS-0602-587"]
    [item] = check_items([("Express parcel, Jakarta\n3 x 64,000.00", None)], words)
    assert item.description.status == "AGREED"
    number = check_value("CFS-0602-587", "text", words)
    assert number is not None and number.status == "AGREED"


def test_a_tilted_line_takes_one_top_and_lines_stay_apart():
    tokens = [
        OcrToken("Printer", 0.13, 0.27, 0.453, 0.480, line=7, space_after=True),
        OcrToken("paper", 0.28, 0.38, 0.463, 0.490, line=7, space_after=True),
        OcrToken("ream", 0.48, 0.58, 0.473, 0.500, line=7, space_after=True),
        OcrToken("TOTAL", 0.10, 0.25, 0.60, 0.63, line=9, space_after=True),
    ]
    words = ocr_words(tokens)
    assert {w.top for w in words[:3]} == {0.463} and {w.bottom for w in words[:3]} == {0.49}
    assert words[3].top == 0.60


def test_tokens_far_apart_stay_two_words_even_without_a_break():
    tokens = [
        OcrToken("SUBTOTAL", 0.10, 0.30, 0.5, 0.52, line=1, space_after=False),
        OcrToken("255,000.00", 0.67, 0.86, 0.5, 0.52, line=1, space_after=True),
    ]
    assert [w.text for w in ocr_words(tokens)] == ["SUBTOTAL", "255,000.00"]
