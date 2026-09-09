"""Регрессия компактного инженерного Excel-экспорта."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.infrastructure.export.engineering_excel_exporter import EngineeringExcelExporter
from app.services.calculation_service import CalculationService


def _result(layer_count: int):
    materials = [
        Material(
            manufacturer="Blank",
            material_name=f"Инженерный слой {i}",
            material_type=MaterialType.PRIMER_ENAMEL,
            binder_type=BinderType.EPOXY,
            density=1.4,
            solids_by_volume_percent=70.0,
            price_per_kg=100.0 + i,
            price_per_liter=140.0 + i,
        )
        for i in range(1, layer_count + 1)
    ]
    obj = ObjectData(object_name="Тест инженерного экспорта", customer="Заказчик", area_m2=100.0)
    layers = [LayerInput(material=m, target_dft=100 + i * 10, losses_percent=5.0) for i, m in enumerate(materials, 1)]
    result, validation = CalculationService().calculate_system(obj, layers)
    assert not validation.has_errors
    return result


def test_engineering_excel_has_two_tables_and_all_layers(tmp_path: Path):
    output = tmp_path / "engineering.xlsx"
    result = _result(4)
    EngineeringExcelExporter().export_system(result, output)

    wb = load_workbook(output, data_only=False)
    assert wb.sheetnames == ["Инженерный расчёт"]
    ws = wb["Инженерный расчёт"]

    assert ws["A5"].value == "Слой"
    assert [ws.cell(row, 2).value for row in range(6, 10)] == [f"Blank Инженерный слой {i}" for i in range(1, 5)]
    assert ws["A10"].value == "ИТОГО"

    summary_header = 13
    assert ws.cell(summary_header, 1).value == "Итог системы"
    labels = [ws.cell(row, 1).value for row in range(summary_header + 1, summary_header + 10)]
    assert "Общая толщина" in labels
    assert "Общий практический расход ЛКМ" in labels
    assert "Общий расход разбавителя" in labels
    assert "Стоимость системы" in labels
    assert "Стоимость объекта" in labels


def test_engineering_excel_does_not_expose_material_prices(tmp_path: Path):
    output = tmp_path / "engineering.xlsx"
    EngineeringExcelExporter().export_system(_result(3), output)
    ws = load_workbook(output, data_only=False)["Инженерный расчёт"]

    values = [cell.value for row in ws.iter_rows() for cell in row]
    assert not any("Цена" in str(value) for value in values if value is not None)
    assert any("Стоимость слоя" in str(value) for value in values if value is not None)


def test_engineering_excel_supports_two_layers(tmp_path: Path):
    output = tmp_path / "engineering.xlsx"
    EngineeringExcelExporter().export_system(_result(2), output)
    ws = load_workbook(output, data_only=False)["Инженерный расчёт"]
    assert [ws.cell(row, 2).value for row in (6, 7)] == ["Blank Инженерный слой 1", "Blank Инженерный слой 2"]
