from app.domain.system_template import SystemTemplateDraft
from app.services.system_book_importer import SystemBookRow, SystemBookSource
from app.services.system_book_mapping import SystemBookColumnMap, SystemBookMapper


def row(number, cells, sheet="Systems"):
    return SystemBookRow(SystemBookSource("books/Системы 2.XLSX", "a" * 64), sheet, number, tuple(cells))


def test_mapper_groups_layers_and_preserves_provenance():
    rows = [
        row(5, ["Система A", "Грунт A", 1, 80, 100, 120, "Maker", "steel", "desc"]),
        row(6, ["Система A", "Эмаль A", 2, 60, 80, 100, "Maker", "steel", "desc"]),
    ]
    columns = SystemBookColumnMap(0, 1, 2, 3, 4, 5, 6, 7, 8)
    drafts = SystemBookMapper.map_rows(rows, columns)
    assert len(drafts) == 1
    draft = drafts[0]
    assert isinstance(draft, SystemTemplateDraft)
    assert draft.status == "DRAFT"
    assert draft.metadata["tds_verified"] == "UNKNOWN"
    assert [layer.layer_number for layer in draft.layers] == [1, 2]
    assert [layer.material_name for layer in draft.layers] == ["Грунт A", "Эмаль A"]
    assert draft.layers[0].source_row == 5
    assert draft.layers[1].source_row == 6
    assert draft.layers[0].source_sha256 == "a" * 64


def test_mapper_keeps_missing_dft_as_unknown_none():
    rows = [row(2, ["Система B", "Материал B", 1, None, None, None])]
    drafts = SystemBookMapper.map_rows(rows, SystemBookColumnMap(0, 1, 2, 3, 4, 5))
    layer = drafts[0].layers[0]
    assert layer.dft_min is None
    assert layer.dft_target is None
    assert layer.dft_max is None


def test_mapper_rejects_invalid_layer_number():
    rows = [row(2, ["Система C", "Материал C", "x"])]
    try:
        SystemBookMapper.map_rows(rows, SystemBookColumnMap(0, 1, 2))
    except ValueError as exc:
        msg = str(exc).lower()
        assert "layer number" in msg or "invalid number" in msg
    else:
        raise AssertionError("invalid layer number must be rejected")


from app.services.system_book_mapping import (
    LayerColumnGroup,
    SideBySideLayout,
    SystemBookSideBySideMapper,
    SYSTEMS2_AKZ_SIDE_BY_SIDE,
)


def _wide_row(number, cells, sheet="АКЗ"):
    return SystemBookRow(SystemBookSource("books/Системы 2.XLSX", "b" * 64), sheet, number, tuple(cells))


def test_side_by_side_expands_present_layers_only():
    # Columns aligned with SYSTEMS2_AKZ_SIDE_BY_SIDE (indices 0..15)
    cells = [None] * 16
    cells[1] = 8
    cells[2] = 'ООО "Колоридо"'
    cells[3] = "Blank Universal"
    cells[4] = 100
    cells[5] = "Эпоксидная грунт эмаль"
    cells[6] = "-"
    cells[7] = "-"
    cells[8] = "-"
    cells[9] = "-"
    cells[10] = "-"
    cells[11] = "-"
    cells[12] = "Blank Finish"
    cells[13] = 50
    cells[14] = "Полиуретановая эмаль"
    cells[15] = "C2, C3, C4"
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(8, cells)], SYSTEMS2_AKZ_SIDE_BY_SIDE, name_prefix="Системы2"
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.status == "DRAFT"
    assert draft.metadata["tds_verified"] == "UNKNOWN"
    assert draft.metadata["source_kind"] == "SYSTEMS_CATALOG_SIDE_BY_SIDE"
    assert draft.metadata["service_conditions"] == "C2, C3, C4"
    assert draft.manufacturer == 'ООО "Колоридо"'
    assert [layer.layer_number for layer in draft.layers] == [1, 2]
    assert [layer.material_name for layer in draft.layers] == ["Blank Universal", "Blank Finish"]
    assert draft.layers[0].dft_target == 100.0
    assert draft.layers[1].dft_target == 50.0
    assert draft.layers[0].source_row == 8
    assert draft.layers[0].source_sha256 == "b" * 64
    assert "Blank Universal" in draft.name
    assert "#8" in draft.name


def test_side_by_side_non_numeric_thickness_becomes_unknown():
    cells = [None] * 16
    cells[1] = 16
    cells[2] = 'ООО "Колоридо"'
    cells[3] = "Blank Universal"
    cells[4] = 180
    cells[5] = "Эпоксидная"
    cells[12] = "Blank Finish"
    cells[13] = "Полиуретановая эмаль"  # anomaly: text in thickness column
    cells[14] = 60
    cells[15] = "C2-C5"
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(16, cells)], SYSTEMS2_AKZ_SIDE_BY_SIDE
    )
    assert len(drafts) == 1
    layer2 = drafts[0].layers[1]
    assert layer2.material_name == "Blank Finish"
    assert layer2.dft_target is None  # UNKNOWN, not invented


def test_side_by_side_skips_row_with_no_materials():
    cells = [None] * 16
    cells[1] = 99
    cells[2] = "Maker"
    cells[3] = "-"
    cells[6] = "-"
    cells[9] = "-"
    cells[12] = "-"
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(99, cells)], SYSTEMS2_AKZ_SIDE_BY_SIDE
    )
    assert drafts == ()


def test_side_by_side_rejects_negative_thickness():
    cells = [None] * 16
    cells[2] = "Maker"
    cells[3] = "Mat"
    cells[4] = -10
    try:
        SystemBookSideBySideMapper.map_rows(
            [_wide_row(1, cells)], SYSTEMS2_AKZ_SIDE_BY_SIDE
        )
    except ValueError as exc:
        assert "negative" in str(exc)
    else:
        raise AssertionError("negative thickness must be rejected")


def test_side_by_side_layout_requires_layers():
    try:
        SystemBookSideBySideMapper.map_rows(
            [_wide_row(1, [None] * 4)],
            SideBySideLayout(manufacturer=0, layers=()),
        )
    except ValueError as exc:
        assert "layers" in str(exc)
    else:
        raise AssertionError("empty layers must be rejected")


from app.services.system_book_mapping import (
    SYSTEMS2_OGZ_SIDE_BY_SIDE,
    SYSTEMS3_AKZ_SIDE_BY_SIDE,
    REVIEWED_SIDE_BY_SIDE_LAYOUTS,
)


def test_optional_number_parses_unit_suffix():
    cells = [None] * 10
    cells[2] = "Maker"
    cells[4] = "Грунт"
    cells[5] = "80 мкм"
    cells[6] = "ОГЗ Mat"
    cells[7] = 3700
    cells[8] = "Finish"
    cells[9] = 50
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(5, cells, sheet="ОГЗ")], SYSTEMS2_OGZ_SIDE_BY_SIDE, name_prefix="Системы2"
    )
    assert len(drafts) == 1
    assert drafts[0].layers[0].dft_target == 80.0
    assert drafts[0].layers[1].dft_target == 3700.0
    assert drafts[0].layers[2].dft_target == 50.0


def test_optional_number_rejects_composite_thickness_as_unknown():
    cells = [None] * 16
    cells[2] = "Maker"
    cells[4] = "Грунт"
    cells[5] = "80 мкм"
    cells[6] = "ЭФФА-КТЭ + ЭФФА ЭП-150"
    cells[7] = "3200 + 2570"
    cells[8] = "Finish"
    cells[9] = 50
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(7, cells, sheet="ОГЗ")], SYSTEMS2_OGZ_SIDE_BY_SIDE
    )
    assert len(drafts) == 1
    assert drafts[0].layers[1].material_name == "ЭФФА-КТЭ + ЭФФА ЭП-150"
    assert drafts[0].layers[1].dft_target is None  # composite → UNKNOWN


def test_systems3_akz_layout_expands_three_layer_row():
    cells = [None] * 14
    cells[0] = 1
    cells[1] = 'ООО "Колоридо"'
    cells[2] = "Грунт-эмаль Blank Universal"
    cells[3] = 110
    cells[4] = "EP"
    cells[5] = "-"
    cells[6] = "-"
    cells[7] = "-"
    cells[8] = "Эмаль Blank Finish"
    cells[9] = 50
    cells[10] = "PU"
    cells[11] = "C2, C3, C4"
    drafts = SystemBookSideBySideMapper.map_rows(
        [_wide_row(8, cells, sheet="АКЗ")], SYSTEMS3_AKZ_SIDE_BY_SIDE, name_prefix="Системы3"
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.status == "DRAFT"
    assert draft.metadata["tds_verified"] == "UNKNOWN"
    assert [l.material_name for l in draft.layers] == [
        "Грунт-эмаль Blank Universal",
        "Эмаль Blank Finish",
    ]
    assert draft.layers[0].dft_target == 110.0
    assert draft.layers[1].dft_target == 50.0
    assert "Системы3" in draft.name


def test_reviewed_layout_registry_keys():
    assert ("Системы 2.XLSX", "АКЗ") in REVIEWED_SIDE_BY_SIDE_LAYOUTS
    assert ("Системы 2.XLSX", "ОГЗ") in REVIEWED_SIDE_BY_SIDE_LAYOUTS
    assert ("Системы 3.xlsx", "АКЗ") in REVIEWED_SIDE_BY_SIDE_LAYOUTS
    assert len(REVIEWED_SIDE_BY_SIDE_LAYOUTS) == 3
