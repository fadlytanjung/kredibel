"""Spreadsheet row counting for intake limits checks (AC-003-3, spec 003 plan).

Counts rows in CSV and XLSX exports to enforce ledgerRowsPerFile before parsing.
Full column mapping and ledger reconciliation is handled in spec 005.
"""

import csv
import io

import openpyxl

from app.domain.file_types import MediaType
from app.ports.spreadsheet_reader import SpreadsheetReader


class DefaultSpreadsheetReader(SpreadsheetReader):
    def count_rows(self, data: bytes, media_type: MediaType) -> int:
        return count_spreadsheet_rows(data, media_type)


def count_spreadsheet_rows(data: bytes, media_type: MediaType) -> int:
    """Count data rows in a CSV or XLSX spreadsheet.

    Excludes empty trailing rows.
    """
    if media_type == MediaType.CSV:
        content = data
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        count = sum(1 for row in reader if any(cell.strip() for cell in row))
        return count

    if media_type == MediaType.XLSX:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        sheet = wb.active
        if sheet is None:
            return 0
        count = 0
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None and str(cell).strip() != "" for cell in row):
                count += 1
        wb.close()
        return count

    return 0
