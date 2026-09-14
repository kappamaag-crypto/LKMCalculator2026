"""Headless smoke regression for the comparison view."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService
from app.ui.views.comparison_view import ComparisonView


def _material(number: int, **kwargs) -> Material:
    return Material(
        id=number,
        manufacturer="Blank",
        material_name=f"Материал {number}",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=100.0 + number,
        **kwargs,
    )


def _layers(count: int) -> list[LayerInput]:
    return [
        LayerInput(material=_material(i), target_dft=100.0 + i * 10, losses_percent=5.0)
        for i in range(1, count + 1)
    ]


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_comparison_view_builds_and_renders_multilayer_result():
    _app()
    service = CalculationService()
    view = ComparisonView(service)
    view.set_object(ObjectData(object_name="Объект", area_m2=100.0))
    view.add_system("Система 2 слоя", _layers(2))
    view.add_system("Система 4 слоя", _layers(4))

    view._on_compare()

    assert view._last_comparison is not None
    assert view.table.columnCount() == 3
    assert view.table.rowCount() > 0
    assert view.table.horizontalHeaderItem(1).text() == "Система 2 слоя"
    assert view.table.horizontalHeaderItem(2).text() == "Система 4 слоя"

    indicators = [view.table.item(row, 0).text() for row in range(view.table.rowCount())]
    assert "Количество слоёв" in indicators
    assert "Слой 4: материал" in indicators
    assert "Мин. температура нанесения, °C" in indicators
    assert view.btn_export.isEnabled()

    view.close()
