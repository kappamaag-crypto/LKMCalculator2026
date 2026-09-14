"""Explicit mapping boundary for reviewed Systems 1-4 workbook rows."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
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

# Reviewed layout for books/Системы 2.XLSX sheet «ОГЗ» (staging only; §15 OGZ calc deferred).
# Data from row 5. Columns 0-based:
# B=№, C=manufacturer, D=metal thickness (not a coating layer),
# E–F=primer, G–H=ОГЗ, I–J=finish, K=R-group, L–N=consumption, O=notes.
# Composite thickness cells (e.g. "3200 + 2570") remain UNKNOWN DFT.
SYSTEMS2_OGZ_SIDE_BY_SIDE = SideBySideLayout(
    manufacturer=2,
    row_number_col=1,
    service_conditions=14,
    layers=(
        LayerColumnGroup(1, material_name=4, thickness=5, material_type=None),
        LayerColumnGroup(2, material_name=6, thickness=7, material_type=None),
        LayerColumnGroup(3, material_name=8, thickness=9, material_type=None),
    ),
)

# Reviewed layout for books/Системы 3.xlsx sheet «АКЗ».
# Header rows 4–7; data from row 8. Columns 0-based:
# A=№, B=manufacturer, C–E=layer1, F–H=layer2, I–K=layer3, L=conditions.
SYSTEMS3_AKZ_SIDE_BY_SIDE = SideBySideLayout(
    manufacturer=1,
    row_number_col=0,
    service_conditions=11,
    layers=(
        LayerColumnGroup(1, material_name=2, thickness=3, material_type=4),
        LayerColumnGroup(2, material_name=5, thickness=6, material_type=7),
        LayerColumnGroup(3, material_name=8, thickness=9, material_type=10),
    ),
)

# Reviewed layout for books/Системы 3.xlsx sheet «ОГЗ» (staging only; §15 OGZ calc deferred).
# Header rows 4–7; data from row 8. Columns 0-based:
# A=№, B=manufacturer, C=metal thickness (not a coating layer),
# D–E=primer, F–G=heat-protect, H–I=fire-protect, J–K=finish, L=R-group.
SYSTEMS3_OGZ_SIDE_BY_SIDE = SideBySideLayout(
    manufacturer=1,
    row_number_col=0,
    service_conditions=11,
    layers=(
        LayerColumnGroup(1, material_name=3, thickness=4, material_type=None),
        LayerColumnGroup(2, material_name=5, thickness=6, material_type=None),
        LayerColumnGroup(3, material_name=7, thickness=8, material_type=None),
        LayerColumnGroup(4, material_name=9, thickness=10, material_type=None),
    ),
)

# Registry of reviewed layouts keyed by (workbook file name, sheet title).
# Системы 1.xls is empty/corrupt (not a real XLS) — no layout.
# Системы 4.xlsx has no usable tabular data in the snapshot — no layout yet.
REVIEWED_SIDE_BY_SIDE_LAYOUTS: dict[tuple[str, str], SideBySideLayout] = {
    ("Системы 2.XLSX", "АКЗ"): SYSTEMS2_AKZ_SIDE_BY_SIDE,
    ("Системы 2.XLSX", "ОГЗ"): SYSTEMS2_OGZ_SIDE_BY_SIDE,
    ("Системы 3.xlsx", "АКЗ"): SYSTEMS3_AKZ_SIDE_BY_SIDE,
    ("Системы 3.xlsx", "ОГЗ"): SYSTEMS3_OGZ_SIDE_BY_SIDE,
}


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
        """Soft parse: missing or non-numeric → None (UNKNOWN). Negative rejected.

        Accepts a single leading number optionally followed by a unit token
        (e.g. ``80 мкм`` → 80.0). Composite cells such as ``3200 + 2570`` stay
        UNKNOWN — no arithmetic is invented.
        """
        value = cls._cell(row, index)
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            number = float(value)
            if number < 0:
                raise ValueError(f"negative thickness in row {row.row_number}: {number}")
            return number
        text = str(value).strip()
        if text in ("-", "—", "–"):
            return None
        # Composite / multi-value → UNKNOWN
        if any(sep in text for sep in ("+", "/", ";")):
            return None
        match = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*(?:[a-zA-Zа-яА-Яµμ°%].*)?$", text)
        if not match:
            return None
        number = float(match.group(1).replace(",", "."))
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


def expand_reviewed_workbook(
    path: str | Path,
    *,
    name_prefix: str | None = None,
) -> tuple[SystemTemplateDraft, ...]:
    """Read a Systems workbook and expand only sheets with a reviewed layout.

    Sheets without an entry in ``REVIEWED_SIDE_BY_SIDE_LAYOUTS`` are skipped
    (not guessed). Returns only DRAFT templates with tds_verified=UNKNOWN.
    """
    from app.services.system_book_importer import SystemBookImporter

    source = Path(path)
    rows = SystemBookImporter().read(source)
    prefix = name_prefix if name_prefix is not None else source.stem
    by_sheet: dict[str, list] = {}
    for row in rows:
        by_sheet.setdefault(row.sheet, []).append(row)

    result: list[SystemTemplateDraft] = []
    for sheet, sheet_rows in by_sheet.items():
        layout = REVIEWED_SIDE_BY_SIDE_LAYOUTS.get((source.name, sheet))
        if layout is None:
            continue
        result.extend(
            SystemBookSideBySideMapper.map_rows(sheet_rows, layout, name_prefix=prefix)
        )
    return tuple(result)
