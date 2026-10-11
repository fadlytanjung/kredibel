"""Page renderer port interface (spec 003 plan).

Renders PDF pages and image uploads into 150 dpi PNGs and 300 px thumbnails,
and performs deterministic triage of each page.
"""

from dataclasses import dataclass
from typing import Protocol

from app.domain.file_types import MediaType
from app.domain.page_triage import TextLayerStatus, WitnessType


@dataclass(frozen=True)
class RenderedPage:
    page_no: int
    image_png: bytes
    thumb_png: bytes
    sha256: str
    text_layer: TextLayerStatus
    blank: bool
    witness: WitnessType


class PageRenderer(Protocol):
    def render_and_triage(
        self,
        data: bytes,
        media_type: MediaType,
    ) -> tuple[int, list[RenderedPage]]:
        """Render and triage pages of a document.

        Returns (total_page_count, list_of_rendered_pages).
        Spreadsheet files return (0, []).
        """
        ...
