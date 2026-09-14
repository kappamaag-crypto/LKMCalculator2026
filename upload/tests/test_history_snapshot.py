"""History snapshot material engineering values (immutable snapshot, current v3 API)."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.infrastructure.database.engine import get_engine, get_session_factory, init_db, session_scope
from app.services.calculation_service import CalculationService
from app.services.history_service import HistoryService


def _sample_result():
    primer = Material(
        id=101,
        material_name="Primer A",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.42,
        solids_by_volume_percent=64.0,
        price_per_kg=650.0,
    )
    result, val = CalculationService().calculate_system(
        ObjectData(object_name="Tank-1", area_m2=100.0),
        [LayerInput(material=primer, target_dft=120.0, losses_percent=0.0)],
    )
    assert not val.has_errors
    result.system.system_name = "System v1"
    return result


def test_history_snapshot_contains_material_engineering_values():
    result = _sample_result()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "snap.sqlite"
        engine = get_engine(db)
        init_db(engine)
        sf = get_session_factory(engine)
        with session_scope(sf) as session:
            calc_id = HistoryService(session).save_calculation(result)
        with session_scope(sf) as session:
            calc = HistoryService(session).get_calculation(calc_id)
            assert calc is not None
            snapshot = json.loads(calc.snapshot_json)

    layer = snapshot["layers"][0]
    assert snapshot["snapshot_version"] == 8
    assert snapshot["system"]["name"] == "System v1"
    assert layer["material_id"] == 101
    assert layer["density"] == pytest.approx(1.42)
    assert layer["solids_by_volume_percent"] == pytest.approx(64.0)
    assert layer["price_per_kg"] == pytest.approx(650.0)
    assert layer["target_dft"] == pytest.approx(120.0)


def test_history_snapshot_is_independent_of_future_catalog_edits():
    result = _sample_result()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "snap_indep.sqlite"
        engine = get_engine(db)
        init_db(engine)
        sf = get_session_factory(engine)
        with session_scope(sf) as session:
            calc_id = HistoryService(session).save_calculation(result)
        with session_scope(sf) as session:
            before = json.loads(
                HistoryService(session).get_calculation(calc_id).snapshot_json
            )["layers"][0]

        # Catalog values may change later; sealed snapshot must not.
        current_catalog_price = 999.0
        assert current_catalog_price != before["price_per_kg"]
        assert before["density"] == pytest.approx(1.42)
        assert before["price_per_kg"] == pytest.approx(650.0)

        with session_scope(sf) as session:
            after = json.loads(
                HistoryService(session).get_calculation(calc_id).snapshot_json
            )["layers"][0]
        assert after["density"] == before["density"]
        assert after["price_per_kg"] == before["price_per_kg"]
        assert after["solids_by_volume_percent"] == before["solids_by_volume_percent"]
