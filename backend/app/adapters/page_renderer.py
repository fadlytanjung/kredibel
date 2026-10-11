"""Page rendering adapter using pypdfium2, pdfplumber and Pillow (spec 003 plan).

Normative references: docs/07 §3.1, docs/09 §7, spec 003.
- Renders pages at 150 dpi (scale ~2.083 from 72 dpi) with long edge capped at 4,000 px.
- Renders thumbnails at 300 px wide.
- Performs page triage (USABLE, UNUSABLE, NONE, blank).
- Checks PDF password encryption (raises EncryptedDocumentError).
"""

import hashlib
import io

import pdfplumber
import pikepdf
import pypdfium2
from PIL import Image

from app.domain.errors import EncryptedDocumentError, ValidationProblem
from app.domain.file_types import MediaType
from app.domain.page_triage import (
    TextLayerStatus,
    WitnessType,
    compute_near_white_ratio,
    triage_page,
)
from app.ports.page_renderer import PageRenderer, RenderedPage

_MAX_LONG_EDGE = 4000
_THUMB_SIZE = (300, 300)
_PDF_DPI_SCALE = 150.0 / 72.0


class DefaultPageRenderer(PageRenderer):
    def render_and_triage(
        self,
        data: bytes,
        media_type: MediaType,
    ) -> tuple[int, list[RenderedPage]]:
        if media_type in (MediaType.XLSX, MediaType.CSV):
            return 0, []

        if media_type in (MediaType.PNG, MediaType.JPEG):
            return self._render_image(data)

        if media_type == MediaType.PDF:
            return self._render_pdf(data)

        return 0, []

    def _render_image(self, data: bytes) -> tuple[int, list[RenderedPage]]:
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Cap long edge at 4000 px
        width, height = img.size
        if max(width, height) > _MAX_LONG_EDGE:
            img.thumbnail((_MAX_LONG_EDGE, _MAX_LONG_EDGE), Image.Resampling.LANCZOS)

        # Full page PNG
        full_buf = io.BytesIO()
        img.save(full_buf, format="PNG")
        image_png = full_buf.getvalue()

        # Thumbnail 300 px
        thumb = img.copy()
        thumb.thumbnail(_THUMB_SIZE, Image.Resampling.LANCZOS)
        thumb_buf = io.BytesIO()
        if thumb.mode not in ("RGB", "L"):
            thumb = thumb.convert("RGB")
        thumb.save(thumb_buf, format="PNG")
        thumb_png = thumb_buf.getvalue()

        near_white_ratio = compute_near_white_ratio(img)
        blank = near_white_ratio >= 0.995
        page_hash = hashlib.sha256(image_png).hexdigest()

        rendered = RenderedPage(
            page_no=1,
            image_png=image_png,
            thumb_png=thumb_png,
            sha256=page_hash,
            text_layer=TextLayerStatus.NONE,
            blank=blank,
            witness=WitnessType.OCR,
        )
        return 1, [rendered]

    def _render_pdf(self, data: bytes) -> tuple[int, list[RenderedPage]]:
        # Password / encryption check with pikepdf
        try:
            with pikepdf.Pdf.open(io.BytesIO(data)) as pdf:
                page_count = len(pdf.pages)
        except pikepdf.PasswordError as err:
            raise EncryptedDocumentError() from err
        except pikepdf.PdfError as err:
            raise ValidationProblem(field="file", message="The file is empty or damaged.") from err

        if page_count == 0:
            return 0, []

        rendered_pages: list[RenderedPage] = []

        # Open for text extraction with pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as plumber_pdf:
            # Open for rasterization with pypdfium2
            pdfium_doc = pypdfium2.PdfDocument(data)
            for page_idx in range(page_count):
                page_no = page_idx + 1

                # Extract text
                extracted_text: str | None = None
                if page_idx < len(plumber_pdf.pages):
                    extracted_text = plumber_pdf.pages[page_idx].extract_text()

                # Render page image at 150 dpi
                pdfium_page = pdfium_doc.get_page(page_idx)
                pil_img = pdfium_page.render(scale=_PDF_DPI_SCALE).to_pil()  # pyright: ignore[reportArgumentType]

                if max(pil_img.size) > _MAX_LONG_EDGE:
                    pil_img.thumbnail((_MAX_LONG_EDGE, _MAX_LONG_EDGE), Image.Resampling.LANCZOS)

                # Full page PNG
                full_buf = io.BytesIO()
                pil_img.save(full_buf, format="PNG")
                image_png = full_buf.getvalue()

                # Thumbnail 300 px
                thumb = pil_img.copy()
                thumb.thumbnail(_THUMB_SIZE, Image.Resampling.LANCZOS)
                thumb_buf = io.BytesIO()
                thumb.save(thumb_buf, format="PNG")
                thumb_png = thumb_buf.getvalue()

                # Triage
                triage = triage_page(text=extracted_text, image=pil_img)
                page_hash = hashlib.sha256(image_png).hexdigest()

                rendered_pages.append(
                    RenderedPage(
                        page_no=page_no,
                        image_png=image_png,
                        thumb_png=thumb_png,
                        sha256=page_hash,
                        text_layer=triage.text_layer,
                        blank=triage.blank,
                        witness=triage.witness,
                    )
                )

        return page_count, rendered_pages
