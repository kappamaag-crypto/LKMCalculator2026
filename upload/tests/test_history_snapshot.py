import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models import (
    BinderType,
    CoatingSystem,
    LayerResult,
    Material,
    ObjectData,
    SystemCalculationResult,
)
from app.infrastructure.database.engine import Base
from app.infrastructure.database import models  # noqa: F401
from app.services.history_service import HistoryService


def _result():
    material = Material(
        id=101,
        manufacturer="Test",
        brand="TestBrand",
        material_name="Material v1",
        binder_type=BinderType.EPOXY,
        density=1.42,
        solids_percent=72.0,
        solids_by_volume_percent=64.0,
        price_per_kg=650.0,
        price_per_liter=923.0,
    )
    layer = LayerResult(
        material=material,
        target_dft=120.0,
        losses_percent=5.0,
        wft=187.5,
        practical_consumption_kg=0.267,
        practical_consumption_l=0.188,
        theoretical_consumption_kg=0.254,
        theoretical_consumption_l=0.179,
        cost_per_m2=173.55,
        total_consumption_kg=0.267,
        total_consumption_l=0.188,
        total_cost=173.55,
    )
    return SystemCalculationResult(
        system=CoatingSystem(system_name="System v1", manufacturer="Test"),
        object_data=ObjectData(
            object_name="Object",
            customer="Customer",
            project="Project",
            calculation_number="CALC-001",
            area_m2=100.0,
        ),
        layers=[layer],
        total_dft=120.0,
        total_theoretical_consumption_kg=0.254,
        total_practical_consumption_kg=0.267,
        total_theoretical_consumption_l=0.179,
        total_practical_consumption_l=0.188,
        total_cost_per_m2=173.55,
        total_cost=17355.0,
    )


def test_history_snapshot_contains_material_engineering_values():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        calc_id = HistoryService(session).save_calculation(_result())
        session.commit()
        calc = HistoryService(session).get_calculation(calc_id)
        snapshot = json.loads(calc.snapshot_json)

    layer = snapshot["layers"][0]
    assert snapshot["snapshot_version"] == 3
    assert snapshot["system"]["name"] == "System v1"
    assert layer["material_id"] == 101
    assert layer["density"] == 1.42
    assert layer["solids_by_volume_percent"] == 64.0
    assert layer["price_per_kg"] == 650.0
    assert layer["target_dft"] == 120.0


def test_history_snapshot_is_independent_of_future_catalog_edits():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        calc_id = HistoryService(session).save_calculation(_result())
        session.commit()
        calc = HistoryService(session).get_calculation(calc_id)
        before = json.loads(calc.snapshot_json)["layers"][0]

        current_catalog_value = 1.90
        assert current_catalog_value != before["density"]
        assert before["price_per_kg"] == 650.0
        assert before["solids_by_volume_percent"] == 64.0
