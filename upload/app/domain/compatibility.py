"""Compatibility rules extracted from the public Kraska.Expert matrix.

The source table is directional: the row is the applied layer and the column is
its previous coating. A blank cell is *unknown*, not a prohibition.

This module deliberately does not turn generic coating knowledge into rules.
Only binder families that can be represented unambiguously by the current
``BinderType`` model are mapped automatically. Materials whose binder taxonomy
is broader or different from the source table return ``UNKNOWN`` until their
technical documentation provides a confirmed compatibility family.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import BinderType, CompatibilityStatus
from .models import Material

SOURCE_URL = "https://kraska.expert/compatibility-tables.html"
SOURCE_TABLE = "Таблица 1. Совместимость ЛКМ с грунтовками"

# Matrix taxonomy. ``epoxy`` is intentionally separate from ``alkyd_epoxy``:
# the source uses the same abbreviation ЭП for both row labels, but they are
# chemically different rows and must not be collapsed in the model.
FAMILY_LABELS: dict[str, str] = {
    "ac": "Алкидно-акриловые (АС)",
    "mc": "Алкидно-стирольные (МС)",
    "au": "Алкидно-уретановые (АУ)",
    "alkyd_epoxy": "Алкидно-эпоксидные (ЭП)",
    "vinyl_chloride": "Винилхлоридные (ХС)",
    "glyptal": "Глифталевые (ГФ)",
    "rosin": "Канифольные (КФ)",
    "rubber": "Каучуковые (КЧ)",
    "silicone": "Кремнийорганические (КО)",
    "oil": "Масляные (МА)",
    "oil_styrene": "Масляно-стирольные (МС)",
    "melamine": "Меламиновые (МЛ)",
    "urea": "Мочевинные (МЧ)",
    "nitrocellulose": "Нитроцеллюлозные (НЦ)",
    "polyacrylic": "Полиакриловые (АК)",
    "polyurethane": "Полиуретановые (УР)",
    "pentaphthalic": "Пентафталевые (ПФ)",
    "epoxy": "Эпоксидные (ЭП)",
}

# Columns are the previous coating (грунтующий слой). The source table has
# 17 columns; there is no separate column for the second ЭП row.
_PREVIOUS_COLUMNS = (
    "ak",
    "ac",
    "au",
    "vg",
    "vl",
    "glyptal",
    "rosin",
    "melamine",
    "mc",
    "urea",
    "pentaphthalic",
    "polyurethane",
    "fl",
    "hv",
    "vinyl_chloride",
    "epoxy",
    "epoxy_ester",
)

# ``+`` = allowed, ``1`` = adhesion check because of different solvents,
# ``2`` = roughening required, ``.`` = blank cell in the source table.
_MATRIX_ROWS = {
    "ac": "+ + . . + + . . . + + . + 1 . + .",
    "mc": "+ + . + . + . . + . + . + . . . .",
    "au": ". . + . + + . . . . . . + . . + .",
    "alkyd_epoxy": "+ . . + + + . . . . + . + . + + +",
    "vinyl_chloride": "+ . . . + + + . . . + . + + + + .",
    "glyptal": "+ . . . + + + . . . + . + 1 . + .",
    "rosin": ". . . . + + + . + . + . + + + + +",
    "rubber": ". . . . + . . . . . . . + . . 2 .",
    "silicone": "+ . . + . . . . . . . . . . . . .",
    "oil": ". . . . + + + . + . + . + . . 2 .",
    "oil_styrene": "+ . . + + + . . + . + . + . . . .",
    "melamine": "+ . . . + + + + + + + . + . . + +",
    "urea": "+ . . . + + + + . + + . + . . + +",
    "nitrocellulose": "+ . . . + 1 + . . . . . + . . . .",
    "polyacrylic": "+ . . . + + . . . + . . + . . + +",
    "polyurethane": "+ . . . + + . . . . + + + . . 2 .",
    "pentaphthalic": "+ . . . + + + . . . + . + 1 . + .",
    "epoxy": "+ . . + + + . + . . + . + 2 + 2 +",
}


@dataclass(frozen=True)
class CompatibilityRule:
    """One directional source-backed compatibility result."""

    previous_family: str
    applied_family: str
    status: CompatibilityStatus
    note: str = ""
    source: str = SOURCE_URL


def _parse_matrix() -> dict[tuple[str, str], CompatibilityRule]:
    rules: dict[tuple[str, str], CompatibilityRule] = {}
    for applied_family, encoded in _MATRIX_ROWS.items():
        values = encoded.split()
        if len(values) != len(_PREVIOUS_COLUMNS):
            raise RuntimeError(
                f"Compatibility row {applied_family!r} has {len(values)} cells; "
                f"expected {len(_PREVIOUS_COLUMNS)}"
            )
        for previous_family, marker in zip(_PREVIOUS_COLUMNS, values):
            if marker == "+":
                status, note = CompatibilityStatus.ALLOWED, "Совместимы"
            elif marker == "1":
                status, note = CompatibilityStatus.WARNING, "Проверить адгезию (разные растворители)"
            elif marker == "2":
                status, note = CompatibilityStatus.WARNING, "Требуется придание шероховатости"
            else:
                continue
            rules[(previous_family, applied_family)] = CompatibilityRule(
                previous_family=previous_family,
                applied_family=applied_family,
                status=status,
                note=note,
            )
    return rules


RULES: dict[tuple[str, str], CompatibilityRule] = _parse_matrix()

# These mappings are deliberately narrow. The source table's taxonomy is
# finer than the current BinderType enum, so a generic ``алкид`` or
# ``цинк-этилсиликат`` is not silently assigned to a row.
BINDER_TO_FAMILY: dict[BinderType, str] = {
    BinderType.EPOXY: "epoxy",
    BinderType.POLYURETHANE: "polyurethane",
    BinderType.ACRYLIC: "polyacrylic",
    BinderType.EPOXY_ESTER: "epoxy_ester",
}


def family_for_binder(binder: BinderType | str | None) -> Optional[str]:
    """Return a source-table family only when the mapping is unambiguous."""
    if binder is None:
        return None
    if not isinstance(binder, BinderType):
        try:
            binder = BinderType(str(binder))
        except ValueError:
            return None
    return BINDER_TO_FAMILY.get(binder)


def family_for_material(material: Material | None) -> Optional[str]:
    if material is None:
        return None
    return family_for_binder(material.binder_type)


def check_binders(
    previous_binder: BinderType | str | None,
    applied_binder: BinderType | str | None,
) -> CompatibilityRule:
    """Check ``previous -> applied`` using the source matrix direction."""
    previous_family = family_for_binder(previous_binder)
    applied_family = family_for_binder(applied_binder)
    if previous_family is None or applied_family is None:
        return CompatibilityRule(
            previous_family=previous_family or "unknown",
            applied_family=applied_family or "unknown",
            status=CompatibilityStatus.UNKNOWN,
            note="Тип связующего не сопоставлен с таксономией исходной таблицы.",
        )
    rule = RULES.get((previous_family, applied_family))
    if rule is not None:
        return rule
    return CompatibilityRule(
        previous_family=previous_family,
        applied_family=applied_family,
        status=CompatibilityStatus.UNKNOWN,
        note="В исходной таблице нет подтверждённой записи для этой пары.",
    )


def check_materials(previous: Material | None, applied: Material | None) -> CompatibilityRule:
    """Check two material objects without inventing a compatibility rule."""
    return check_binders(
        previous.binder_type if previous else None,
        applied.binder_type if applied else None,
    )


def validate_matrix_integrity() -> None:
    """Fail fast if the transcribed source matrix is accidentally malformed."""
    if len(_MATRIX_ROWS) != len(FAMILY_LABELS):
        raise RuntimeError("Compatibility family labels and matrix rows are out of sync")
    if len(_PREVIOUS_COLUMNS) != 17:
        raise RuntimeError("The source table must contain 17 previous-layer columns")


validate_matrix_integrity()
