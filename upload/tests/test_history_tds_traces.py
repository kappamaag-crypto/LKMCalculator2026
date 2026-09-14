"""HistoryService sealed snapshot TDS traces (§12/§14/§25)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.domain.enums import BinderType, MaterialType
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.infrastructure.database.engine import Base
from app.infrastructure.database import models  # noqa: F401
from app.services.history_service import HistoryService

def _result(name):
    m = Material(
        id=1, manufacturer="Blank", brand="Blank", material_name=name,
        material_type=MaterialType.PRIMER, binder_type=BinderType.EPOXY, density=1.4,
        solids_percent=70, solids_by_volume_percent=65, price_per_kg=500, price_per_liter=700,
    )
    lr = LayerResult(
        material=m, target_dft=120, losses_percent=5, wft=180,
        practical_consumption_kg=0.3, practical_consumption_l=0.2,
        theoretical_consumption_kg=0.28, theoretical_consumption_l=0.19,
        cost_per_m2=150, total_consumption_kg=0.3, total_consumption_l=0.2, total_cost=150,
    )
    return SystemCalculationResult(
        system=CoatingSystem(system_name="S", manufacturer="Blank"),
        object_data=ObjectData(object_name="O", area_m2=10), layers=[lr], total_dft=120,
        total_theoretical_consumption_kg=0.28, total_practical_consumption_kg=0.3,
        total_theoretical_consumption_l=0.19, total_practical_consumption_l=0.2,
        total_cost_per_m2=150, total_cost=1500,
    )

def test_history_tds_known_for_blank_universal():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        cid = HistoryService(s).save_calculation(_result("Blank Universal primer"))
        s.commit()
        assert HistoryService(s).get_calculation_tds_verified(cid) == "KNOWN"
        traces = HistoryService(s).get_calculation_tds_traces(cid)
        assert traces[0]["document_id"] == "BLANK_UNIVERSAL_TDS"
