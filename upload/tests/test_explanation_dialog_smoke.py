"""Headless smoke regression for the Explanation Engine dialog."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService
from app.ui.dialogs.explanation_dialog import ExplanationDialog


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_explanation_dialog_renders_source_traceable_report():
    _app()
    material = Material(
        id=1,
        manufacturer="Blank",
        material_name="Грунт",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=None,
    )
    service = CalculationService()
    result, validation = service.calculate_system(
        ObjectData(object_name="Объект", area_m2=100.0),
        [LayerInput(material=material, target_dft=100.0, losses_percent=0.0)],
    )
    assert not validation.has_errors

    report = service.explain_calculation(result)
    dialog = ExplanationDialog(report)

    text = dialog.text.toPlainText()
    assert "Explanation overall:" in text
    assert "LAYER_DFT_BASIS" in text
    assert "COST_UNKNOWN" in text
    assert "Промежуточные значения v3 не округляются" in text

    dialog.close()
