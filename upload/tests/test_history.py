"""Тесты HistoryService (SQLite)."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import pytest
from app.domain.models import Material, ObjectData
from app.domain.enums import MaterialType, BinderType
from app.domain.calculator import LayerInput
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME
from app.services.calculation_service import CalculationService
sqlalchemy = pytest.importorskip("sqlalchemy")
from app.services.history_service import HistoryService
from app.infrastructure.database.engine import get_engine, init_db, get_session_factory, session_scope

@pytest.fixture
def sample_result():
    primer = Material(material_name="Грунт Test", material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY, density=1.4, solids_percent=73.0, solids_by_volume_percent=73.0, price_per_kg=500.0, packaging_kg=20.0)
    result, val = CalculationService().calculate_system(ObjectData(object_name="Тест истории", area_m2=50.0, calculation_number="H-001"), [LayerInput(material=primer, target_dft=100)])
    assert not val.has_errors
    return result

def test_save_and_list(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"hist.sqlite"; engine=get_engine(db); init_db(engine); sf=get_session_factory(engine)
        with session_scope(sf) as session:
            svc=HistoryService(session); calc_id=svc.save_calculation(sample_result, notes="unit test"); assert calc_id>0; rows=svc.list_calculations(); assert len(rows)>=1; assert rows[0].object_name=="Тест истории"; assert rows[0].total_dft==sample_result.total_dft
        with session_scope(sf) as session:
            calc=HistoryService(session).get_calculation(calc_id); assert calc is not None; assert len(calc.layers)==1; assert "Грунт" in calc.layers[0].material_name

def test_unknown_cost_is_preserved_as_null(sample_result):
    sample_result.layers[0].material.price_per_kg=None; sample_result.total_cost_per_m2=None; sample_result.total_cost=None
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"unknown_cost.sqlite"; engine=get_engine(db); init_db(engine); sf=get_session_factory(engine)
        with session_scope(sf) as session: calc_id=HistoryService(session).save_calculation(sample_result)
        with session_scope(sf) as session:
            calc=HistoryService(session).get_calculation(calc_id); assert calc is not None; assert calc.total_cost is None; assert calc.total_cost_per_m2 is None

def test_snapshot_contains_thinner_information():
    primer=Material(material_name="Грунт 2K", material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY, density=1.4, solids_percent=73.0, solids_by_volume_percent=73.0, price_per_kg=500.0)
    thinner=Material(material_name="Разбавитель Test", material_type=MaterialType.THINNER, binder_type=BinderType.OTHER, density=0.9, price_per_kg=None)
    result,val=CalculationService().calculate_system(ObjectData(object_name="Тест разбавителя", area_m2=10.0), [LayerInput(material=primer,target_dft=100,thinner_percent=10,thinner=thinner,thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME)])
    assert not val.has_errors
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"thinner.sqlite"; engine=get_engine(db); init_db(engine); sf=get_session_factory(engine)
        with session_scope(sf) as session: calc_id=HistoryService(session).save_calculation(result)
        with session_scope(sf) as session:
            calc=HistoryService(session).get_calculation(calc_id); layer=json.loads(calc.snapshot_json)["layers"][0]; assert layer["thinner_name"]=="Разбавитель Test"; assert layer["thinner_density"]==0.9; assert layer["thinner_price_per_kg"] is None; assert layer["thinner_percent"]==10; assert layer["thinner_consumption_l"]>0

def test_unknown_area_is_preserved_as_null(sample_result):
    sample_result.object_data.area_m2 = None
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"unknown_area.sqlite"; engine=get_engine(db); init_db(engine); sf=get_session_factory(engine)
        with session_scope(sf) as session:
            calc_id=HistoryService(session).save_calculation(sample_result)
            calc=HistoryService(session).get_calculation(calc_id)
            assert calc is not None
            assert calc.area_m2 is None
            snapshot=json.loads(calc.snapshot_json)
            assert snapshot["object"]["area_m2"] is None

def test_delete(sample_result):
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/"hist2.sqlite"; engine=get_engine(db); init_db(engine); sf=get_session_factory(engine)
        with session_scope(sf) as session:
            svc=HistoryService(session); calc_id=svc.save_calculation(sample_result); svc.delete_calculation(calc_id)
        with session_scope(sf) as session: assert HistoryService(session).get_calculation(calc_id) is None
