"""Spreadsheet reader port interface for limits checking (spec 003 plan).

Counts rows in CSV and XLSX exports to enforce ledgerRowsPerFile before parsing.
"""

from typing import Protocol

from app.domain.file_types import MediaType


class SpreadsheetReader(Protocol):
    def count_rows(self, data: bytes, media_type: MediaType) -> int:
        """Count non-empty rows in a CSV or XLSX spreadsheet."""
        ...
