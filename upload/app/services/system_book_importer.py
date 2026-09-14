"""Read the ``books/Системы 1–4`` workbooks without inventing engineering data.

The reader is deliberately a staging boundary: it extracts workbook rows and
immutable source identity, but does not guess which columns mean material,
DFT, system name, or applicability. A later reviewed mapping step may convert
rows into materials/system templates.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

import openpyxl


SUPPORTED_BOOK_NAMES = (
    "Системы 1.xls",
    "Системы 2.XLSX",
    "Системы 3.xlsx",
    "Системы 4.xlsx",
)


@dataclass(frozen=True)
class SystemBookSource:
    path: str
    sha256: str


@dataclass(frozen=True)
class SystemBookRow:
    source: SystemBookSource
    sheet: str
    row_number: int
    cells: tuple[Any, ...]


class SystemBookImporter:
    """Extract source rows from the Systems 1–4 workbooks.

    No cell is converted into a material or system automatically. In
    particular, blank cells remain blank and ambiguous rows are retained for
    review instead of being promoted to a calculated value.
    """

    def __init__(self, allowed_names: Iterable[str] = SUPPORTED_BOOK_NAMES):
        self.allowed_names = frozenset(allowed_names)

    @staticmethod
    def source_identity(path: Path) -> SystemBookSource:
        data = path.read_bytes()
        return SystemBookSource(path=path.as_posix(), sha256=sha256(data).hexdigest())

    def read(self, path: str | Path) -> tuple[SystemBookRow, ...]:
        source_path = Path(path)
        if source_path.name not in self.allowed_names:
            raise ValueError(f"Неизвестный файл каталога систем: {source_path.name}")
        source = self.source_identity(source_path)
        suffix = source_path.suffix.lower()
        if suffix == ".xlsx":
            return self._read_xlsx(source_path, source)
        if suffix == ".xls":
            return self._read_xls(source_path, source)
        raise ValueError(f"Неподдерживаемый формат книги: {source_path.suffix}")

    @staticmethod
    def _read_xlsx(path: Path, source: SystemBookSource) -> tuple[SystemBookRow, ...]:
        workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
        rows: list[SystemBookRow] = []
        try:
            for sheet in workbook.worksheets:
                for row_number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
                    cells = tuple(values)
                    if any(value not in (None, "") for value in cells):
                        rows.append(SystemBookRow(source, sheet.title, row_number, cells))
        finally:
            workbook.close()
        return tuple(rows)

    @staticmethod
    def _read_xls(path: Path, source: SystemBookSource) -> tuple[SystemBookRow, ...]:
        try:
            import xlrd
        except ImportError as exc:
            raise RuntimeError("Legacy XLS import requires xlrd") from exc
        workbook = xlrd.open_workbook(path.as_posix(), on_demand=True)
        rows: list[SystemBookRow] = []
        try:
            for sheet in workbook.sheets():
                for row_number in range(sheet.nrows):
                    cells = tuple(sheet.row_values(row_number))
                    if any(value not in (None, "") for value in cells):
                        rows.append(SystemBookRow(source, sheet.name, row_number + 1, cells))
        finally:
            workbook.release_resources()
        return tuple(rows)
