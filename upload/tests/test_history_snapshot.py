import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.models import (
    LayerInput,
    ObjectData,
    SystemCalculationResult,
    SystemInput,
)
from app.infrastructure.database.models import Base
from app.services.history_service import HistoryService


def _result() -> SystemCalculationResult:
    system = SystemInput(
        system_name="System v1",
        layers=[
            LayerInput(
                material_id=101,
                material_name="Primer A",
                density=1.42,
                solids_by_volume_percent=64.0,
                price_per_kg=650.0,
                target_dft=120.0,
            )
        ],
    )
    return SystemCalculationResult(
        system=system,
        object_data=ObjectData(object_name="Tank-1", area_m2=100.0),
        layers=[],
        total_dft=120.0,
        total_cost_per_m2=10.0,
        total_cost=1000.0,
        total_paint_kg=5.0,
        warnings=[],
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
    assert snapshot["snapshot_version"] == 8
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
        before = json.loads(HistoryService(session).get_calculation(calc_id).snapshot_json)["layers"][0]

    # Simulate catalog price/density change after the calculation was saved.
    current_catalog_value = 999.0
    assert current_catalog_value != before["density"]
    assert before["price_per_kg"] == 650.0
    assert before["solids_by_volume_percent"] == 64.0
