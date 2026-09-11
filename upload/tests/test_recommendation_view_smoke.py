"""Headless smoke for RecommendationView recommendation details."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.models import CoatingSystem, LayerDefinition, Material
from app.domain.enums import BinderType, CorrosionCategory, DurabilityLevel, EnvironmentType, MaterialType, SurfaceType
from app.services.recommendation_service import RecommendationService
from app.ui.views.recommendation_view import RecommendationView


def make_system():
    material = Material(material_name="Smoke material", material_type=MaterialType.PRIMER, binder_type=BinderType.EPOXY, density=1.4, solids_percent=70.0, solids_by_volume_percent=70.0)
    return CoatingSystem(id=1, system_name="Smoke system", corrosion_categories=[CorrosionCategory.C4], durability=DurabilityLevel.HIGH, temperature_min=-40, temperature_max=60, surface_types=[SurfaceType.NEW_STEEL], environments=[EnvironmentType.OUTDOOR], layers=[LayerDefinition(layer_number=1, target_dft=80.0, material=material)], number_of_layers=1)


def test_recommendation_view_accepts_optional_chemical_values():
    app = QApplication.instance() or QApplication([])
    view = RecommendationView(RecommendationService())
    view.set_systems([make_system()])
    view.ed_chemical_agent.setText("AGENT")
    view.ed_chemical_concentration.setText("")
    view.ed_chemical_temperature.setText("")
    view._on_recommend()
    assert view._last_result is not None
    assert view.list_results.count() == 1
    assert "не найдено" in view.list_results.item(0).text().lower()
    view.deleteLater()
    app.processEvents()


def test_recommendation_view_displays_score_breakdown():
    app = QApplication.instance() or QApplication([])
    view = RecommendationView(RecommendationService())
    view.set_systems([make_system()])
    view._on_recommend()
    assert view._last_result is not None
    assert view._last_result.items
    details = view.txt_details.toPlainText()
    assert "Разбивка оценки:" in details
    assert "Коррозионная категория:" in details
    assert "Долговечность:" in details
    assert "Технологичность:" in details
    assert "Стоимость:" in details
    assert "Итоговый Score:" in details
    view.deleteLater()
    app.processEvents()
