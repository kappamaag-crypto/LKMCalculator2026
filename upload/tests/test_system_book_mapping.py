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
        assert "layer number" in str(exc)
    else:
        raise AssertionError("invalid layer number must be rejected")
