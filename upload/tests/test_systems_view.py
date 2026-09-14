from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from app.infrastructure.database.engine import Base, get_engine, get_session_factory
from app.infrastructure.database.models import (
    CoatingSystemLayerORM,
    CoatingSystemORM,
    MaterialORM,
)
from app.ui.views import systems_view
from app.ui.views.systems_view import SystemsView


@dataclass
class FakeMaterial:
    id: int
    name: str
    material_type: str = "грунт"
    recommended_dft_min: float = 60.0
    recommended_dft_max: float = 120.0

    def display_name(self) -> str:
        return self.name


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _materials():
    return [
        FakeMaterial(1, "Материал 1"),
        FakeMaterial(2, "Материал 2", material_type="промежуточный"),
        FakeMaterial(3, "Материал 3", material_type="эмаль"),
    ]


def _prepare_db(tmp_path):
    engine = get_engine(tmp_path / "systems_view.sqlite")
    Base.metadata.create_all(bind=engine)
    factory = get_session_factory(engine)

    with factory() as session:
        for material in _materials():
            session.add(
                MaterialORM(
                    id=material.id,
                    material_name=material.name,
                    material_type=material.material_type,
                    manufacturer="Test",
                )
            )
        system = CoatingSystemORM(
            system_name="Тестовая система",
            manufacturer="Test",
            number_of_layers=3,
            is_active=True,
        )
        system.layers = [
            CoatingSystemLayerORM(layer_number=1, material_id=1, target_dft=70, thinner_percent=5),
            CoatingSystemLayerORM(layer_number=2, material_id=2, target_dft=90, thinner_percent=10),
            CoatingSystemLayerORM(layer_number=3, material_id=3, target_dft=110, thinner_percent=0),
        ]
        session.add(system)
        session.commit()
        system_id = system.id

    return engine, factory, system_id


def _names(view: SystemsView):
    return [view.table.item(row, 1).text() for row in range(view.table.rowCount())]


def test_reorder_save_reload_and_copy_preserve_system_layers(monkeypatch, tmp_path, qapp):
    _engine, factory, system_id = _prepare_db(tmp_path)
    monkeypatch.setattr(systems_view, "get_session_factory", lambda: factory)

    view = SystemsView(_materials())
    index = view.list_systems.findData(system_id)
    assert index >= 0
    view.list_systems.setCurrentIndex(index)
    assert _names(view) == ["Материал 1", "Материал 2", "Материал 3"]

    view.table.selectRow(1)
    view._move_layer(-1)
    assert _names(view) == ["Материал 2", "Материал 1", "Материал 3"]
    assert [view.table.item(row, 0).text() for row in range(3)] == ["1", "2", "3"]

    view._save()
    assert view._current_id == system_id

    reloaded = SystemsView(_materials())
    assert reloaded.list_systems.findData(system_id) >= 0
    reloaded.list_systems.setCurrentIndex(reloaded.list_systems.findData(system_id))
    assert _names(reloaded) == ["Материал 2", "Материал 1", "Материал 3"]
    assert [reloaded.table.item(row, 0).text() for row in range(3)] == ["1", "2", "3"]

    reloaded._copy_selected()
    assert reloaded._current_id is None
    assert reloaded.ed_name.text().endswith("— копия")
    assert _names(reloaded) == ["Материал 2", "Материал 1", "Материал 3"]
    assert [reloaded.table.item(row, 3).text() for row in range(3)] == ["90.0", "70.0", "110.0"]
    assert [reloaded.table.item(row, 5).text() for row in range(3)] == ["10.00", "5.00", "0.00"]


def test_from_calculation_creates_unsaved_draft_without_recalculation(monkeypatch, tmp_path, qapp):
    _engine, factory, _system_id = _prepare_db(tmp_path)
    monkeypatch.setattr(systems_view, "get_session_factory", lambda: factory)

    materials = _materials()
    result = SimpleNamespace(
        system=SimpleNamespace(
            system_name="Расчётная система",
            manufacturer="Calc",
            description="Из расчёта",
            substrate="Сталь",
            standards="ГОСТ",
            certificate="Сертификат",
        ),
        layers=[
            SimpleNamespace(material=materials[0], target_dft=75.5, thinner_percent=4),
            SimpleNamespace(material=materials[1], target_dft=95.25, thinner_percent=8),
            SimpleNamespace(material=materials[2], target_dft=115.0, thinner_percent=0),
        ],
    )

    view = SystemsView(materials)
    view.set_calculation_result(result)
    assert view.btn_from_calculation.isEnabled()

    view._from_calculation()
    assert view._current_id is None
    assert view.ed_name.text() == "Расчётная система — из расчёта"
    assert _names(view) == ["Материал 1", "Материал 2", "Материал 3"]
    assert [view.table.item(row, 3).text() for row in range(3)] == ["75.5", "95.2", "115.0"]
    assert [view.table.item(row, 5).text() for row in range(3)] == ["4.00", "8.00", "0.00"]
