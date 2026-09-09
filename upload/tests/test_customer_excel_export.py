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
    ws["B1"] = "Если стоимость в КГ"
    ws["B15"] = "Если стоимость в литрах"
    ws["B16"] = "Система АКЗ"
    headers = ["Площадь", "Система покрытия", "Связующее", "Цвет", "Плотность", "Сухой остаток", "Толщина пленки", "", "Укрывистость", "Потери", "Практ", "Цена с НДС за кг", "Цена с НДС за литр", "Теоретический расход", "Теоретический расход", "Расход с учетом потерь", "Стоимость с учетом потерь %, с НДС"]
    for col, value in enumerate(headers, 2):
        ws.cell(3, col, value)
        ws.cell(17, col, value)
    for row in (6, 20):
        for col, value in enumerate(["м2", "слой", "", "RAL", "кг/л", "%", "мкм", "мкм", "м2/л", "%", "м2/л", "Руб", "Руб", "л/м2", "кг/м2", "кг/м2", "Руб/м2"], 2):
            ws.cell(row, col, value)
    for row in (9, 10, 23, 24):
        ws.cell(row, 2, "Разбавитель")
    for row in (11, 25):
        ws.cell(row, 3, "Толщина покрытия (мкм)")
        ws.cell(row, 10, "Общее количество ЛКМ")
    for rng in ("B1:R1", "B15:R15", "B16:Q16", "B3:B5", "C3:C5", "D3:D5", "E3:E5", "F3:F5", "G3:G5", "H3:I3", "J3:L3", "M3:M5", "N3:N5", "O3:O5", "P3:P5", "Q3:Q5", "R3:R5", "B9:E9", "G9:L9", "B10:E10", "G10:L10", "C11:H11", "J11:L11", "B17:B19", "C17:C19", "D17:D19", "E17:E19", "F17:F19", "G17:G19", "H17:I17", "J17:L17", "M17:M19", "N17:N19", "O17:O19", "P17:P19", "Q17:Q19", "R17:R19", "B23:E23", "G23:L23", "B24:E24", "G24:L24", "C25:H25", "J25:L25"):
        ws.merge_cells(rng)
    for cell in ("C7", "C8", "C21", "C22"):
        ws[cell].fill = PatternFill("solid", fgColor="FFF2CC")
    for cell in ("C9", "C10", "C23", "C24"):
        ws[cell].fill = PatternFill("solid", fgColor="E2F0D9")
    wb.save(path)


def _result(layer_count: int):
    materials = [
        Material(
            manufacturer="Blank",
            material_name=f"Слой {i}",
            material_type=MaterialType.PRIMER_ENAMEL,
            binder_type=BinderType.EPOXY,
            density=1.4,
            solids_by_volume_percent=70.0,
            price_per_kg=100.0 + i,
            price_per_liter=140.0 + i,
        )
        for i in range(1, layer_count + 1)
    ]
    obj = ObjectData(object_name="Тест", customer="Заказчик", area_m2=100.0)
    layers = [LayerInput(material=m, target_dft=100 + i * 10, losses_percent=5.0) for i, m in enumerate(materials, 1)]
    result, validation = CalculationService().calculate_system(obj, layers)
    assert not validation.has_errors
    return result


def _export(tmp_path: Path, layer_count: int):
    template = tmp_path / "template.xlsx"
    _template(template)
    output = tmp_path / f"result_{layer_count}.xlsx"
    settings = AppSettings(report_mode="full", excel_template_path=str(template))
    CustomerExcelExporter(settings).export_calculation(_result(layer_count), output)
    return load_workbook(output, data_only=False)["База"]


def test_customer_excel_preserves_two_layer_form(tmp_path):
    ws = _export(tmp_path, 2)
    assert ws["C7"].value == "Blank Слой 1"
    assert ws["C8"].value == "Blank Слой 2"
    assert ws["C11"].value == "Толщина покрытия (мкм)"
    assert ws["C25"].value == "Толщина покрытия (мкм)"


def test_customer_excel_expands_to_three_layers_without_truncation(tmp_path):
    ws = _export(tmp_path, 3)
    assert [ws.cell(row, 3).value for row in range(7, 10)] == [f"Blank Слой {i}" for i in range(1, 4)]
    assert [ws.cell(row, 3).value for row in range(23, 26)] == [f"Blank Слой {i}" for i in range(1, 4)]
    assert ws["C13"].value == "Толщина покрытия (мкм)"
    assert ws["C29"].value == "Толщина покрытия (мкм)"
    assert ws["B17"].value == "Если стоимость в литрах"
    assert ws["B18"].value.startswith("Система АКЗ:")


def test_customer_excel_expands_to_four_layers_and_keeps_styles(tmp_path):
    ws = _export(tmp_path, 4)
    assert [ws.cell(row, 3).value for row in range(7, 11)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert [ws.cell(row, 3).value for row in range(25, 29)] == [f"Blank Слой {i}" for i in range(1, 5)]
    assert ws["C15"].value == "Толщина покрытия (мкм)"
    assert ws["C33"].value == "Толщина покрытия (мкм)"
    assert ws["C9"].fill.fgColor.rgb == ws["C8"].fill.fgColor.rgb
    assert ws["C11"].fill.fgColor.rgb == ws["C9"].fill.fgColor.rgb


def test_customer_excel_contains_all_layers_even_with_mixed_thinners(tmp_path):
    ws = _export(tmp_path, 4)
    assert ws.max_row == 33
    assert all(ws.cell(row, 3).value is not None for row in (7, 8, 9, 10, 25, 26, 27, 28))
