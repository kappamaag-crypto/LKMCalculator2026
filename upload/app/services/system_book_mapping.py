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


@dataclass(frozen=True)
class LayerColumnGroup:
    """Explicit 0-based column indices for one layer block in a side-by-side sheet."""

    layer_number: int
    material_name: int
    thickness: Optional[int] = None
    material_type: Optional[int] = None


@dataclass(frozen=True)
class SideBySideLayout:
    """Reviewed explicit layout for one sheet of one Systems workbook.

    Never inferred from headers at runtime — only applied after human review.
    """

    manufacturer: int
    row_number_col: Optional[int] = None
    service_conditions: Optional[int] = None
    layers: tuple[LayerColumnGroup, ...] = ()
    empty_markers: tuple[str, ...] = ("-", "—", "–", "")


# Reviewed layout for books/Системы 2.XLSX sheet «АКЗ».
# Header rows 3–6; data from row 7. Columns 0-based:
# B=№, C=manufacturer, D–F=layer1, G–I=layer2, J–L=layer3, M–O=layer4, P=conditions.
SYSTEMS2_AKZ_SIDE_BY_SIDE = SideBySideLayout(
    manufacturer=2,
    row_number_col=1,
    service_conditions=15,
    layers=(
        LayerColumnGroup(1, material_name=3, thickness=4, material_type=5),
        LayerColumnGroup(2, material_name=6, thickness=7, material_type=8),
        LayerColumnGroup(3, material_name=9, thickness=10, material_type=11),
        LayerColumnGroup(4, material_name=12, thickness=13, material_type=14),
    ),
)


class SystemBookSideBySideMapper:
    """Expand reviewed side-by-side layer columns into DRAFT SystemTemplateDraft.

    One workbook data row → one DRAFT template with sequential layers.
    Blank / dash material cells are skipped (not UNKNOWN material).
    Non-numeric thickness → dft_* = None (UNKNOWN), never invented.
    status is always DRAFT; tds_verified is always UNKNOWN.
    """

    @staticmethod
    def _cell(row: SystemBookRow, index: Optional[int]):
        if index is None:
            return None
        if index < 0 or index >= len(row.cells):
            return None
        return row.cells[index]

    @classmethod
    def _text(cls, row: SystemBookRow, index: Optional[int], default: str = "") -> str:
        value = cls._cell(row, index)
        if value in (None, ""):
            return default
        return str(value).strip() or default

    @classmethod
    def _optional_number(cls, row: SystemBookRow, index: Optional[int]) -> Optional[float]:
        """Soft parse: missing or non-numeric → None (UNKNOWN). Negative rejected."""
        value = cls._cell(row, index)
        if value in (None, ""):
            return None
        if isinstance(value, str) and value.strip() in ("-", "—", "–"):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if number < 0:
            raise ValueError(f"negative thickness in row {row.row_number}: {number}")
        return number

    @classmethod
    def _is_empty_material(cls, text: str, markers: tuple[str, ...]) -> bool:
        return text.strip() in markers or text.strip() == ""

    @classmethod
    def map_rows(
        cls,
        rows: Sequence[SystemBookRow],
        layout: SideBySideLayout,
        *,
        name_prefix: str = "SYSTEMS",
    ) -> tuple[SystemTemplateDraft, ...]:
        if not layout.layers:
            raise ValueError("SideBySideLayout.layers must not be empty")

        result: list[SystemTemplateDraft] = []
        for row in sorted(rows, key=lambda r: r.row_number):
            manufacturer = cls._text(row, layout.manufacturer)
            conditions = cls._text(row, layout.service_conditions)
            seq = cls._text(row, layout.row_number_col)
            layers: list[TemplateLayer] = []
            sequential = 0
            for group in layout.layers:
                material = cls._text(row, group.material_name)
                if cls._is_empty_material(material, layout.empty_markers):
                    continue
                sequential += 1
                thickness = cls._optional_number(row, group.thickness)
                layers.append(
                    TemplateLayer(
                        layer_number=sequential,
                        material_name=material,
                        dft_min=None,
                        dft_target=thickness,
                        dft_max=None,
                        source_path=row.source.path,
                        source_sheet=row.sheet,
                        source_row=row.row_number,
                        source_sha256=row.source.sha256,
                    )
                )
            if not layers:
                continue
            primary = layers[0].material_name
            name_parts = [name_prefix, row.sheet]
            if seq:
                name_parts.append(f"#{seq}")
            name_parts.append(primary)
            name = "/".join(name_parts)
            meta = {
                "source_kind": "SYSTEMS_CATALOG_SIDE_BY_SIDE",
                "tds_verified": "UNKNOWN",
            }
            if conditions:
                meta["service_conditions"] = conditions
            if seq:
                meta["catalog_row_number"] = seq
            draft = SystemTemplateDraft(
                name=name,
                manufacturer=manufacturer,
                description=conditions,
                substrate="",
                source_path=row.source.path,
                source_sheet=row.sheet,
                source_row=row.row_number,
                source_sha256=row.source.sha256,
                layers=tuple(layers),
                notes="SYSTEMS_CATALOG: side-by-side expand; review and TDS/ND verification required",
                status="DRAFT",
                metadata=meta,
            )
            draft.validate()
            result.append(draft)
        return tuple(result)
