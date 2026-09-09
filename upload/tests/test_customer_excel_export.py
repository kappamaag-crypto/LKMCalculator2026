"""Регрессия пользовательского Excel-шаблона ``База`` для 2/3/4+ слоёв."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from app.config import AppSettings
from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.infrastructure.export.customer_excel_exporter import CustomerExcelExporter
from app.services.calculation_service import CalculationService


def _template(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "База"
    ws["B1"] = "Расчёт системы АКЗ"
    headers = ["Площадь", "Система покрытия", "Связующее", "Цвет", "Плотность", "Сухой остаток", "Толщина пленки", "", "Укрывистость", "Потери", "Практ", "Цена с НДС за кг", "Цена с НДС за литр", "Теоретический расход", "Теоретический расход", "Расход с учетом потерь", "Стоимость с учетом потерь %, с НДС"]
    for col, value in enumerate(headers, 2):
        ws.cell(3, col, value)
    for col, value in enumerate(["м2", "слой", "", "RAL", "кг/л", "%", "мкм", "мкм", "м2/л", "%", "м2/л", "Руб", "Руб", "л/м2", "кг/м2", "кг/м2", "Руб/м2"], 2):
        ws.cell(6, col, value)
    for row in (9, 10):
        ws.cell(row, 2, "Разбавитель")
    ws["C11"] = "Толщина покрытия (мкм)"
    ws["J11"] = "Общее количество ЛКМ"
    for rng in ("B1:R1", "B3:B5", "C3:C5", "D3:D5", "E3:E5", "F3:F5", "G3:G5", "H3:I3", "J3:L3", "M3:M5", "N3:N5", "O3:O5", "P3:P5", "Q3:Q5", "R3:R5", "B9:E9", "G9:L9", "B10:E10", "G10:L10", "C11:H11", "J11:L11"):
        ws.merge_cells(rng)
    for cell in ("C7", "C8"):
        ws[cell].fill = PatternFill("solid", fgColor="FFF2CC")
    # Для merged-cell заливка должна находиться на top-left anchor: именно
    # это сохраняется в XLSX и доступно экспортеру после load_workbook().
    for cell in ("B9", "B10"):
        ws[cell].fill = PatternFill("solid", fgColor="E2F0D9")
    wb.save(path)


def _result(layer_count: int, with_mixed_thinners: bool = False, long_name: bool = False):
    materials = [
        Material(
            manufacturer="Blank",
            material_name=(
                "Сверхдлинное наименование антикоррозионного материала для проверки "
                "переноса полного названия без усечения "
                if long_name and i == 1
                else f"Слой {i}"
            ),
            material_type=MaterialType.PRIMER_ENAMEL,
            binder_type=BinderType.EPOXY,
            density=1.4,
            solids_by_volume_percent=70.0,
            price_per_kg=100.0 + i,
            price_per_liter=140.0 + i,
        )
        for i in range(1, layer_count + 1)
    ]
    thinner = Material(
        manufacturer="Blank",
        material_name="Разбавитель универсальный",
        material_type=MaterialType.THINNER,
        density=0.9,
        price_per_kg=50.0,
    )
    obj = ObjectData(object_name="Тест", customer="Заказчик", area_m2=100.0)
    layers = [
        LayerInput(
            material=m,
            target_dft=100 + i * 10,
            losses_percent=5.0,
            thinner_percent=5.0 if with_mixed_thinners and i % 2 == 1 else 0.0,
            thinner=thinner if with_mixed_thinners and i % 2 == 1 else None,
        )
        for i, m in enumerate(materials, 1)
    ]
    result, validation = CalculationService().calculate_system(obj, layers)
    assert not validation.has_errors
    return result


def _export(tmp_path: Path, layer_count: int, with_mixed_thinners: bool = False, mode: str = "full", long_name: bool = False):
    template = tmp_path / "template.xlsx"
    _template(template)
    output = tmp_path / f"result_{layer_count}_{mode}.xlsx"
    settings = AppSettings(report_mode=mode, excel_template_path=str(template))
    CustomerExcelExporter(settings).export_calculation(
        _result(layer_count, with_mixed_thinners, long_name), output
    )
    return load_workbook(output, data_only=False)


def test_customer_excel_is_single_table(tmp_path):
    ws = _export(tmp_path, 2)["База"]
    assert ws["B1"].value == "Расчёт системы АКЗ"
    assert ws.max_row == 11
    assert ws["C7"].value == "Blank Слой 1"
    assert ws["C8"].value == "Blank Слой 2"
    assert ws["C11"].value == "Толщина покрытия (мкм)"
    assert all("Если стоимость" not in str(cell.value or "") for row in ws.iter_rows() for cell in row)


def test_customer_excel_expands_to_three_layers_without_truncation(tmp_path):
    ws = _export(tmp_path, 3)["База"]
    assert [ws.cell(row, 3).value for row in range(7, 10)] == [f"Blank Слой {i}" for i in range(1, 4)]
    assert ws["C13"].value == "Толщина покрытия (мкм)"
    assert ws.max_row == 13


def test_customer_excel_expands_to_four_layers_and_keeps_styles(tmp_path):
    ws = _export(tmp_path, 4)["База"]
    assert [ws.cell(row, 3).value for row in range(7, 11)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert ws["C15"].value == "Толщина покрытия (мкм)"
    assert ws.max_row == 15
    assert ws["C9"].fill.fgColor.rgb == "00FFF2CC"
    assert ws["B11"].fill.fgColor.rgb == "00E2F0D9"
    assert ws["B12"].fill.fgColor.rgb == "00E2F0D9"
    assert "B11:E11" in {str(rng) for rng in ws.merged_cells.ranges}


def test_customer_excel_contains_all_layers_even_with_mixed_thinners(tmp_path):
    ws = _export(tmp_path, 4, with_mixed_thinners=True)["База"]
    assert ws.max_row == 15
    assert [ws.cell(row, 3).value for row in range(7, 11)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert ws["B11"].value == "Разбавитель для Blank Слой 1"
    assert ws["B12"].value is None
    assert ws["B13"].value == "Разбавитель для Blank Слой 3"
    assert ws["B14"].value is None
    assert ws["O11"].value is not None
    assert ws["O13"].value is not None


def test_customer_excel_preserves_long_material_name(tmp_path):
    wb = _export(tmp_path, 2, long_name=True)
    ws = wb["База"]
    expected = "Сверхдлинное наименование антикоррозионного материала для проверки переноса полного названия без усечения"
    assert ws["C7"].value == f"Blank {expected}"


def test_customer_excel_commercial_and_full_keep_price_fields(tmp_path):
    for mode in ("commercial", "full"):
        ws = _export(tmp_path, 2, mode=mode)["База"]
        assert ws["M7"].value == 101.0
        assert ws["N7"].value == 141.0
        assert all("Если стоимость" not in str(cell.value or "") for row in ws.iter_rows() for cell in row)


def test_customer_excel_engineering_mode_uses_separate_export(tmp_path):
    wb = _export(tmp_path, 3, mode="engineering")
    assert wb.sheetnames == ["Инженерный расчёт"]
    ws = wb["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in range(6, 9)] == [f"Blank Слой {i}" for i in range(1, 4)]
    values = [cell.value for row in ws.iter_rows() for cell in row]
    assert not any("Цена" in str(value) for value in values if value is not None)
