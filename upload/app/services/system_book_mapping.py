"""Explicit mapping boundary for reviewed Systems 1-4 workbook rows."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_book_importer import SystemBookRow

@dataclass(frozen=True)
class SystemBookColumnMap:
    system_name: int
    material_name: int
    layer_number: int
    dft_min: Optional[int] = None
    dft_target: Optional[int] = None
    dft_max: Optional[int] = None
    manufacturer: Optional[int] = None
    substrate: Optional[int] = None
    description: Optional[int] = None

class SystemBookMapper:
    """Map only explicitly assigned columns; never infer workbook semantics."""
    @staticmethod
    def _cell(row: SystemBookRow, index: Optional[int]):
        if index is None:
            return None
        if index < 0 or index >= len(row.cells):
            raise ValueError(f"column index {index} outside row {row.row_number}")
        return row.cells[index]

    @classmethod
    def _text(cls, row: SystemBookRow, index: Optional[int], default: str = "") -> str:
        value = cls._cell(row, index)
        return default if value in (None, "") else str(value).strip() or default

    @classmethod
    def _number(cls, row: SystemBookRow, index: Optional[int]) -> Optional[float]:
        value = cls._cell(row, index)
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid number in row {row.row_number}: {value!r}") from exc
        if number < 0:
            raise ValueError(f"negative number in row {row.row_number}: {number}")
        return number

    @classmethod
    def map_rows(cls, rows: Sequence[SystemBookRow], columns: SystemBookColumnMap) -> tuple[SystemTemplateDraft, ...]:
        """Create DRAFT templates grouped by source file, sheet and explicit system name."""
        grouped: dict[tuple[str, str, str], list[SystemBookRow]] = {}
        for row in rows:
            name = cls._text(row, columns.system_name, "UNKNOWN")
            if name == "UNKNOWN":
                raise ValueError(f"missing system name in row {row.row_number}")
            grouped.setdefault((row.source.path, row.sheet, name), []).append(row)

        result: list[SystemTemplateDraft] = []
        for (path, sheet, name), source_rows in grouped.items():
            source_rows = sorted(source_rows, key=lambda r: r.row_number)
            layers: list[TemplateLayer] = []
            for row in source_rows:
                layer_value = cls._number(row, columns.layer_number)
                if layer_value is None or not layer_value.is_integer() or layer_value < 1:
                    raise ValueError(f"invalid layer number in row {row.row_number}")
                layers.append(TemplateLayer(
                    layer_number=int(layer_value),
                    material_name=cls._text(row, columns.material_name, "UNKNOWN"),
                    dft_min=cls._number(row, columns.dft_min),
                    dft_target=cls._number(row, columns.dft_target),
                    dft_max=cls._number(row, columns.dft_max),
                    source_path=row.source.path,
                    source_sheet=row.sheet,
                    source_row=row.row_number,
                    source_sha256=row.source.sha256,
                ))
            first = source_rows[0]
            draft = SystemTemplateDraft(
                name=name,
                manufacturer=cls._text(first, columns.manufacturer),
                description=cls._text(first, columns.description),
                substrate=cls._text(first, columns.substrate),
                source_path=path,
                source_sheet=sheet,
                source_row=first.row_number,
                source_sha256=first.source.sha256,
                layers=tuple(layers),
                notes="SYSTEMS_CATALOG: review and TDS/ND verification required",
                status="DRAFT",
                metadata={"source_kind": "SYSTEMS_CATALOG", "tds_verified": "UNKNOWN"},
            )
            draft.validate()
            result.append(draft)
        return tuple(result)
