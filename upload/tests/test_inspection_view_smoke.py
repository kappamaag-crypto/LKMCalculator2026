"""Headless smoke coverage for the §32 DFT inspection UI workflow."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.models import Material, ObjectData, CoatingSystem, LayerResult, SystemCalculationResult
from app.domain.inspection import DFT_OVERALL_OK, DftMeasurementPoint
from app.ui.views.inspection_view import InspectionView


def test_inspection_view_evaluates_dft_against_latest_calculation():
    app = QApplication.instance() or QApplication([])
    material = Material(
        material_name="Coat",
        density=1.4,
        solids_by_volume_percent=60.0,
        recommended_dft_min=80.0,
        recommended_dft_max=150.0,
    )
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="S"),
        object_data=ObjectData(area_m2=10.0),
        layers=[LayerResult(material=material, target_dft=120.0, wft=200.0)],
        total_dft=120.0,
    )
    view = InspectionView()
    view.set_calculation_result(result)
    view._points = [DftMeasurementPoint(0, "P1", measured_dft_um=110.0)]
    view._evaluate_dft()
    text = view.summary.toPlainText()
    assert "DFT inspection overall: OK" in text
    assert "P1" in text
    assert view.service.evaluate_dft_against_calculation(view._points, result).overall_status == DFT_OVERALL_OK
    view.deleteLater()
    app.processEvents()
