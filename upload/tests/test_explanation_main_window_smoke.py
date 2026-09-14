"""Headless acceptance smoke for the Explanation Engine menu path."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService
import app.ui.main_window as main_window_module
from app.ui.main_window import MainWindow


def _app() -> QApplication:
    app = QApplication.instance()
    return app if app is not None else QApplication([])


def test_main_window_explanation_action_uses_latest_system_calculation(monkeypatch):
    _app()
    shown: list[object] = []

    class StubDialog:
        def __init__(self, report, parent=None):
            shown.append((report, parent))

        def exec(self):
            return 0

    monkeypatch.setattr(main_window_module, "ExplanationDialog", StubDialog)
    # MainWindow eagerly constructs the catalogue review tab. Its constructor may
    # surface unrelated catalogue-import errors through a modal QMessageBox,
    # which blocks a headless/offscreen acceptance test before the target menu
    # path is exercised. The catalogue workflow has its own tests; keep this
    # smoke focused on the Explanation Engine integration.
    monkeypatch.setattr(
        main_window_module.SystemCatalogReviewView,
        "reload",
        lambda self: None,
    )

    window = MainWindow()
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
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="Объект", area_m2=100.0),
        [LayerInput(material=material, target_dft=100.0, losses_percent=0.0)],
    )
    assert not validation.has_errors
    window._last_calculation_result = result

    window._show_calculation_explanation()

    assert len(shown) == 1
    report, parent = shown[0]
    assert parent is window
    assert any(item.code == "LAYER_DFT_BASIS" for item in report.items)
    assert any(item.code == "COST_UNKNOWN" for item in report.items)
    assert any(
        action.text() == "Пояснение расчёта…"
        for action in window.menuBar().actions()
        if action.menu() is not None
        for action in action.menu().actions()
    )
    window.close()
