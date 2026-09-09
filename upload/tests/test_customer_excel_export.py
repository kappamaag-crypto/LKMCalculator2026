"""Регрессия customer-facing Excel-экспорта."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.infrastructure.export.customer_excel_exporter import CustomerExcelExporter
from app.services.calculation_service import CalculationService


def _template(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "База"
    for row in range(1, 26):
        for col in range(1, 22):
            ws.cell(row, col, f"T{row}:{col}")
    ws.merge_cells("B7:E7")
    ws.merge_cells("B8:E8")
    ws.merge_cells("B9:E9")
    ws.merge_cells("B10:E10")
    ws.merge_cells("B11:R11")
    ws.merge_cells("B15:E15")
    ws.merge_cells("B16:E16")
    ws.merge_cells("B17:E17")
    ws.merge_cells("B18:E18")
    ws.merge_cells("B19:R19")
    ws["C7"].fill = PatternFill("solid", fgColor="FFFF00")
    ws["C8"].fill = PatternFill("solid", fgColor="FFFF00")
    ws["B9"].fill = PatternFill("solid", fgColor="00FF00")
    ws["B10"].fill = PatternFill("solid", fgColor="00FF00")
    wb.save(path)
    return path


def _result(layer_count: int, with_mixed_thinners: bool = False, long_name: bool = False):
    materials = []
    for i in range(1, layer_count + 1):
        materials.append(Material(
            id=i,
            manufacturer="Blank",
            brand="Blank",
            material_name=("Очень длинное наименование материала " + "X" * 180) if long_name and i == 1 else f"Слой {i}",
            material_type=MaterialType.PRIMER_ENAMEL,
            binder_type=BinderType.EPOXY,
            density=1.4,
            solids_by_volume_percent=70.0,
            price_per_kg=100.0 + i,
            price_per_liter=140.0 + i,
        ))
    thinner = Material(
        id=100,
        manufacturer="Blank",
        brand="Blank",
        material_name="Разбавитель",
        material_type=MaterialType.THINNER,
        density=0.9,
        price_per_kg=50.0,
    )
    obj = ObjectData(object_name="Тестовый объект", customer="Заказчик", project="Проект", area_m2=100.0)
    layers = []
    for i, material in enumerate(materials, 1):
        use_thinner = with_mixed_thinners and i % 2 == 1
        layers.append(LayerInput(material=material, target_dft=100 + i * 10, losses_percent=5.0, thinner_percent=5.0 if use_thinner else 0.0, thinner=thinner if use_thinner else None))
    result, validation = CalculationService().calculate_system(obj, layers)
    assert not validation.has_errors
    return result


def _export(tmp_path: Path, layer_count: int, mode: str = "engineering", mixed: bool = False, long_name: bool = False):
    template = _template(tmp_path / "КалькуляторЭКСЕЛЛЬ.xlsx")
    output = tmp_path / f"out_{mode}_{layer_count}.xlsx"
    result = _result(layer_count, with_mixed_thinners=mixed, long_name=long_name)
    CustomerExcelExporter(template).export_calculation(result, output, report_mode=mode)
    return load_workbook(output, data_only=False)


def test_customer_excel_is_single_table(tmp_path):
    wb = _export(tmp_path, 2, mode="engineering")
    assert wb.sheetnames == ["Инженерный расчёт"]


def test_customer_excel_expands_to_three_layers_without_truncation(tmp_path):
    wb = _export(tmp_path, 3, mode="engineering")
    ws = wb["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in range(6, 9)] == [f"Blank Слой {i}" for i in range(1, 4)]


def test_customer_excel_expands_to_four_layers_and_keeps_styles(tmp_path):
    wb = _export(tmp_path, 4, mode="engineering")
    ws = wb["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in range(6, 10)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert ws["A10"].value == "ИТОГО"


def test_customer_excel_contains_all_layers_even_with_mixed_thinners(tmp_path):
    wb = _export(tmp_path, 4, mode="engineering", mixed=True)
    ws = wb["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in range(6, 10)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert ws["I6"].value == "Blank Разбавитель"
    assert ws["I7"].value == "—"
    assert ws["I8"].value == "Blank Разбавитель"
    assert ws["I9"].value == "—"


def test_customer_excel_preserves_long_material_name(tmp_path):
    wb = _export(tmp_path, 2, mode="engineering", long_name=True)
    ws = wb["Инженерный расчёт"]
    assert "Очень длинное наименование материала" in ws["B6"].value


def test_customer_excel_commercial_and_full_keep_price_fields(tmp_path):
    for mode in ("commercial", "full"):
        wb = _export(tmp_path, 2, mode=mode)
        ws = wb["База"]
        values = [cell.value for row in ws.iter_rows() for cell in row]
        assert 101.0 in values
        assert 141.0 in values
        assert not any("Если стоимость" in str(value) for value in values if value is not None)


def test_customer_excel_engineering_mode_uses_separate_export(tmp_path):
    wb = _export(tmp_path, 3, mode="engineering")
    assert wb.sheetnames == ["Инженерный расчёт"]
    ws = wb["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in range(6, 9)] == [f"Blank Слой {i}" for i in range(1, 4)]
    values = [cell.value for row in ws.iter_rows() for cell in row]
    assert not any("Цена" in str(value) for value in values if value is not None)


def test_customer_excel_has_deterministic_print_area_for_four_layers(tmp_path):
    # The exported customer-facing sheet is the legacy-formatted branch; use commercial mode.
    wb = _export(tmp_path, 4, mode="commercial")
    ws = wb["База"]
    assert str(ws.print_area) == "'База'!$B$1:$R$15"
    assert ws.print_title_rows == "$1:$6"
    assert ws.sheet_properties.pageSetUpPr.fitToPage is True
    assert ws.page_setup.fitToWidth == 1
    assert ws.page_setup.fitToHeight == 0
