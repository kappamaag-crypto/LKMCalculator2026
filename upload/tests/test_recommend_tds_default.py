from app.domain.enums import CorrosionCategory, DurabilityLevel, MaterialType
from app.domain.models import CoatingSystem, LayerDefinition, Material, ObjectData
from app.services.recommendation_service import RecommendationService

def _mat(name, **kw):
    v = dict(material_name=name, material_type=MaterialType.PRIMER, manufacturer="Blank", density=1.4,
             solids_by_volume_percent=70, recommended_dft_min=20, recommended_dft_max=400, max_single_layer_dft=500)
    v.update(kw); return Material(**v)
def _obj():
    return ObjectData(corrosion_category=CorrosionCategory.C3, durability=DurabilityLevel.MEDIUM,
                      surface_temperature=20, air_temperature=20, relative_humidity=60, dew_point=15)
def _sys(name, material, dft):
    return CoatingSystem(system_name=name, corrosion_categories=[CorrosionCategory.C3], durability=DurabilityLevel.MEDIUM,
                         layers=[LayerDefinition(material=material, layer_number=1, target_dft=dft)])

def test_recommend_excludes_out_of_tds_by_default():
    bad = _sys("Finish bad", _mat("Blank Finish topcoat"), 200)
    good = _sys("Finish ok", _mat("Blank Finish topcoat"), 70)
    names = [i.system.system_name for i in RecommendationService().recommend(_obj(), [bad, good]).items]
    assert "Finish ok" in names and "Finish bad" not in names

def test_filter_rejects_out_of_range():
    fr = RecommendationService().filter_with_known_tds(_obj(), [_sys("F", _mat("Blank Finish topcoat"), 200)])[0]
    assert fr.passed is False
