"""Tests for page triage domain logic (AC-003-4, Spec 003 T003-02, docs/07 §3.1).

Triage rules:
1. pdfplumber finds >= 40 characters and >= 80% are printable and decodable (no (cid:…) glyphs)
   -> textLayer = USABLE, witness = TEXT_LAYER
2. Characters exist but fail the test above
   -> textLayer = UNUSABLE, witness = OCR
3. No characters (scan or image)
   -> textLayer = NONE, witness = OCR
4. Rendered page is >= 99.5% near-white and has no characters
   -> blank = True (saves a model call)
"""

from PIL import Image

from app.domain.page_triage import (
    TextLayerStatus,
    WitnessType,
    compute_near_white_ratio,
    triage_page,
)


def test_triage_usable_text_layer() -> None:
    # Printable ASCII characters without (cid:...) glyphs
    sample_text = (
        "This is a clean bank statement page with plenty of readable text for account 1234567890."
    )
    assert len(sample_text) >= 40

    result = triage_page(text=sample_text, near_white_ratio=0.85)

    assert result.text_layer == TextLayerStatus.USABLE
    assert result.witness == WitnessType.TEXT_LAYER
    assert result.blank is False
    assert result.char_count == len(sample_text)
    assert result.printable_ratio >= 0.80


def test_triage_unusable_few_characters() -> None:
    # Only 11 characters (< 40 threshold)
    sample_text = "Invoice 123"

    result = triage_page(text=sample_text, near_white_ratio=0.90)

    assert result.text_layer == TextLayerStatus.UNUSABLE
    assert result.witness == WitnessType.OCR
    assert result.blank is False
    assert result.char_count == 11


def test_triage_unusable_cid_glyphs() -> None:
    # 30 (cid:...) unmapped glyphs + 15 readable characters = 45 total glyphs
    # Decodable ratio = 15 / 45 = 33.3% (< 80%)
    cid_glyphs = "".join(f"(cid:{i})" for i in range(30))
    sample_text = f"{cid_glyphs}Total: $1,250.00"

    result = triage_page(text=sample_text, near_white_ratio=0.88)

    assert result.text_layer == TextLayerStatus.UNUSABLE
    assert result.witness == WitnessType.OCR
    assert result.blank is False
    assert result.printable_ratio < 0.80


def test_triage_usable_with_acceptable_cid_glyphs() -> None:
    # 5 (cid:...) glyphs + 95 readable characters = 100 total glyphs
    # Decodable ratio = 95 / 100 = 95% (>= 80%) and total >= 40
    cid_glyphs = "".join(f"(cid:{i})" for i in range(5))
    readable = "A" * 95
    sample_text = f"{cid_glyphs}{readable}"

    result = triage_page(text=sample_text, near_white_ratio=0.88)

    assert result.text_layer == TextLayerStatus.USABLE
    assert result.witness == WitnessType.TEXT_LAYER
    assert result.blank is False
    assert result.printable_ratio >= 0.80


def test_triage_unusable_unprintable_control_chars() -> None:
    # 50 characters, but 20 are unprintable control bytes (\x00, \x01...)
    # Printable ratio = 30 / 50 = 60% (< 80%)
    sample_text = ("\x00\x01\x02\x03" * 5) + ("Standard legible text line here!" * 1)

    result = triage_page(text=sample_text, near_white_ratio=0.80)

    assert result.text_layer == TextLayerStatus.UNUSABLE
    assert result.witness == WitnessType.OCR
    assert result.blank is False
    assert result.printable_ratio < 0.80


def test_triage_image_only_no_characters() -> None:
    # 0 characters, content on page (near_white_ratio < 0.995)
    result = triage_page(text="", near_white_ratio=0.75)

    assert result.text_layer == TextLayerStatus.NONE
    assert result.witness == WitnessType.OCR
    assert result.blank is False
    assert result.char_count == 0


def test_triage_blank_page() -> None:
    # 0 characters and >= 99.5% near-white
    result = triage_page(text="", near_white_ratio=0.999)

    assert result.text_layer == TextLayerStatus.NONE
    assert result.witness == WitnessType.OCR
    assert result.blank is True


def test_triage_near_white_with_characters_is_not_blank() -> None:
    # Rendered page looks almost white, but has readable text
    result = triage_page(text="Small text in corner", near_white_ratio=0.998)

    assert result.blank is False
    assert result.char_count > 0


def test_triage_chars_sequence() -> None:
    # Passing sequence of character strings (like pdfplumber page.chars)
    chars = ["(cid:1)"] * 40 + ["A"] * 10
    result = triage_page(chars=chars, near_white_ratio=0.90)

    assert result.text_layer == TextLayerStatus.UNUSABLE
    assert result.witness == WitnessType.OCR
    assert result.char_count == 50
    assert result.printable_ratio == 0.20


def test_compute_near_white_ratio_blank_image() -> None:
    # 100x100 purely white image (all 255)
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    ratio = compute_near_white_ratio(img)
    assert ratio == 1.0

    result = triage_page(text=None, image=img)
    assert result.blank is True
    assert result.text_layer == TextLayerStatus.NONE


def test_compute_near_white_ratio_non_blank_image() -> None:
    # 100x100 white image with a 20x20 black block (400 black pixels / 10,000 = 4% black)
    # Near-white ratio = 96% (< 99.5%)
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    for x in range(20):
        for y in range(20):
            img.putpixel((x, y), (0, 0, 0))

    ratio = compute_near_white_ratio(img)
    assert ratio == 0.96

    result = triage_page(text=None, image=img)
    assert result.blank is False
    assert result.text_layer == TextLayerStatus.NONE
