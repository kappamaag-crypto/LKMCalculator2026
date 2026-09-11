from app.domain.compatibility import (
    FAMILY_LABELS,
    SOURCE_SNAPSHOT,
    SOURCE_TABLE,
    SOURCE_URL,
    _MATRIX_ROWS,
    _PREVIOUS_COLUMNS,
    RULES,
)
from app.domain.enums import CompatibilityStatus


EXPECTED_ROWS = {
    "ac": "+ + . . + + . . . + + . + 1 . + .",
    "mc": "+ + . + . + . . + . + . + . . . .",
    "au": ". . + . + + . . . . . . + . . + .",
    "alkyd_epoxy": "+ . . + + + . . . . + . + . + + +",
    "vinyl_chloride": "+ . . . + + + . . . + . + + + + .",
    "glyptal": "+ . . . + + + . . . + . + 1 . + .",
    "rosin": ". . . . + + + . + . + . + + + + .",
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


def test_source_identity_points_to_project_snapshot_and_published_table():
    assert SOURCE_SNAPSHOT == "books/совместимость_лкм.png"
    assert SOURCE_TABLE == "Таблица 1. Совместимость ЛКМ с грунтовками"
    assert SOURCE_URL == "https://www.lkm-prof.ru/razdel/sovmestim.php"


def test_matrix_is_exactly_transcribed_from_source_snapshot():
    assert _MATRIX_ROWS == EXPECTED_ROWS
    assert len(_PREVIOUS_COLUMNS) == 17
    assert len(FAMILY_LABELS) == 18
    assert len(_MATRIX_ROWS) == 18
    assert all(len(row.split()) == 17 for row in _MATRIX_ROWS.values())


def test_blank_source_cell_remains_unknown_and_special_markers_are_warnings():
    assert ("epoxy", "epoxy") in RULES
    assert RULES[("epoxy", "epoxy")].status is CompatibilityStatus.WARNING
    assert RULES[("epoxy", "epoxy")].note == "Требуется придание шероховатости"

    assert RULES[("hv", "ac")].status is CompatibilityStatus.WARNING
    assert RULES[("hv", "ac")].note == "Проверить адгезию (разные растворители)"

    # The source has a blank cell for alkyd -> epoxy because alkyd is not
    # unambiguously mapped to one source family in the current BinderType model.
    assert ("unknown", "epoxy") not in RULES
