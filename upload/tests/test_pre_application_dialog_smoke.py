from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.domain.enums import MaterialType
from app.domain.engineering_context import EngineeringContext
from app.services.calculation_service import CalculationService
from app.ui.dialogs.pre_application_dialog import PreApplicationDialog


def test_pre_application_dialog_renders_incomplete_without_invented_data():
    app = QApplication.instance() or QApplication([])
    material = Material(
        material_name="Test primer",
        material_type=MaterialType.PRIMER,
        recommended_dft_min=100,
        recommended_dft_max=200,
    )
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="Test system"),
        object_data=ObjectData(object_name="Test object"),
        layers=[LayerResult(material=material, target_dft=150)],
        total_dft=150,
        engineering_context=EngineeringContext(),
    )

    dialog = PreApplicationDialog(CalculationService(), result)

    assert "INCOMPLETE" in dialog.status_label.text()
    text = dialog.report.toPlainText()
    assert "PRE_AMBIENT_UNKNOWN" in text
    assert "PRE_SURFACE_PREP_UNKNOWN" in text
    assert "PRE_MATERIAL_LIMITS_UNKNOWN" in text
    assert "3 °C" not in text

    dialog.close()
    app.processEvents()
