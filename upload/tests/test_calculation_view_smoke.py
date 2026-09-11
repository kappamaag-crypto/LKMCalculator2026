"""Headless smoke regression for the main calculation workflow."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import CoatingSystem, LayerDefinition, Material
from app.services.calculation_service import CalculationService
from app.ui.views.calculation_view import CalculationView


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def _material(number: int, name: str, dft_min: float, dft_max: float) -> Material:
    return Material(
        id=number,
        manufacturer="Blank",
        brand="Blank",
        material_name=name,
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=100.0 + number,
        recommended_dft_min=dft_min,
        recommended_dft_max=dft_max,
    )


def test_calculation_view_calculates_and_enables_result_actions():
    _app()
    service = CalculationService()
    view = CalculationView(service)
    primer = _material(1, "Грунт", 100.0, 200.0)
    finish = _material(2, "Эмаль", 60.0, 100.0)
    view.set_materials([primer, finish])

    view.cmb_material.setCurrentIndex(0)
    view._on_add_layer()
    view.cmb_material.setCurrentIndex(1)
    view._on_add_layer()
    view.ed_object.setText("Объект")
    view.ed_system_name.setText("Грунт + Эмаль")
    view.spin_area.setValue(100.0)

    assert view._recalculate(False, False) is True
    assert view._last_result is not None
    assert view.layer_table.rowCount() == 2
    assert view.btn_excel.isEnabled()
    assert view.btn_pdf.isEnabled()
    assert view.btn_to_cmp.isEnabled()
    assert "Толщина:" in view.lbl_summary.text()

    view.close()


def test_calculation_view_loads_saved_system_into_editable_calculation():
    _app()
    service = CalculationService()
    view = CalculationView(service)
    primer = _material(1, "Грунт", 100.0, 200.0)
    finish = _material(2, "Эмаль", 60.0, 100.0)
    system = CoatingSystem(
        id=10,
        system_name="Сохранённая система",
        layers=[
            LayerDefinition(material_id=1, material=primer, layer_number=1, target_dft=150.0),
            LayerDefinition(material_id=2, material=finish, layer_number=2, target_dft=80.0),
        ],
        number_of_layers=2,
    )
    view.set_materials([primer, finish])
    view.set_systems([system])
    view.cmb_system.setCurrentIndex(1)
    view.spin_area.setValue(250.0)

    view._on_load_saved_system()

    assert view.layer_table.rowCount() == 2
    assert view.ed_system_name.text() == "Сохранённая система"
    assert view._last_result is not None
    assert view.btn_to_cmp.isEnabled()

    view.close()
