"""Headless smoke for scenario compatibility presentation."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.domain.calculation_scenario import CalculationScenario
from app.domain.compatibility import CompatibilityRule
from app.domain.enums import BinderType, CompatibilityStatus, MaterialType
from app.domain.layer_compatibility import LayerCompatibilityReport, LayerDefinition, LayerTransitionResult
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.ui.views.calculation_scenario_view import CalculationScenarioView


def make_material(name: str, binder: BinderType) -> Material:
    return Material(material_name=name, material_type=MaterialType.PRIMER, binder_type=binder, density=1.4, solids_by_volume_percent=70.0)


def make_system() -> CoatingSystem:
    primer = make_material("Primer", BinderType.EPOXY)
    finish = make_material("Finish", BinderType.POLYURETHANE)
    return CoatingSystem(id=1, system_name="Scenario system", number_of_layers=2, layers=[
        LayerDefinition(material_id=1, material=primer, layer_number=1, target_dft=100.0),
        LayerDefinition(material_id=2, material=finish, layer_number=2, target_dft=80.0),
    ])


def make_result(system: CoatingSystem) -> SystemCalculationResult:
    return SystemCalculationResult(system=system, object_data=ObjectData(area_m2=1.0), layers=[
        LayerResult(material=layer.material, target_dft=layer.target_dft or 100.0) for layer in system.layers
    ])


class StubScenarioService:
    def evaluate(self, scenario: CalculationScenario):
        system = scenario.alternatives[0]
        result = make_result(system)
        previous, applied = system.layers
        report = LayerCompatibilityReport(transitions=(LayerTransitionResult(
            previous_layer_index=1, applied_layer_index=2,
            previous_material=previous.material, applied_material=applied.material,
            rule=CompatibilityRule(previous_family="epoxy", applied_family="polyurethane", status=CompatibilityStatus.WARNING, note="Проверить окно перекрытия"),
        ),))
        return SimpleNamespace(alternatives=(SimpleNamespace(result=result, compatibility=report),))


def test_scenario_view_surfaces_compatibility_status_and_notes():
    app = QApplication.instance() or QApplication([])
    view = CalculationScenarioView(StubScenarioService())
    view.set_systems([make_system()])
    view.table_systems.item(0, 0).setCheckState(Qt.Checked)
    view._calculate()

    assert view.table_result.item(6, 0).text() == "Совместимость"
    assert view.table_result.item(6, 1).text() == "WARNING (1)"
    assert "Проверить окно перекрытия" in view.table_result.item(7, 1).text()
    assert view.btn_cmp.isEnabled()

    view.deleteLater()
    app.processEvents()
