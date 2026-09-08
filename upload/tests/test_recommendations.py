"""Тесты recommendation engine."""
from __future__ import annotations
from app.domain.models import CoatingSystem,LayerDefinition,ObjectData,Material
from app.domain.enums import CorrosionCategory,DurabilityLevel,SurfaceType,EnvironmentType,MaterialType,BinderType
from app.domain.recommendation.rules import filter_system
from app.domain.recommendation.scorer import score_system
from app.domain.recommendation.recommender import RecommendationEngine

def make_material(n="Test coating"):
    return Material(material_name=n,material_type=MaterialType.PRIMER,binder_type=BinderType.EPOXY,density=1.4,solids_percent=70.0)
def make_system(name,categories,durability,layers_count=2,t_min=-40,t_max=60,surfaces=None):
    mat=make_material(f"{name} material")
    layers=[LayerDefinition(layer_number=i+1,target_dft=80.0,material=mat) for i in range(layers_count)]
    return CoatingSystem(id=hash(name)%10000,system_name=name,corrosion_categories=categories,durability=DurabilityLevel(durability) if durability else None,temperature_min=t_min,temperature_max=t_max,surface_types=surfaces or [SurfaceType.NEW_STEEL],environments=[EnvironmentType.OUTDOOR],layers=layers,number_of_layers=layers_count)
class TestFilter:
    def test_pass_c4_high(self):
        sys=make_system("Sys C4 High",[CorrosionCategory.C4],"High"); obj=ObjectData(corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH,surface_type=SurfaceType.NEW_STEEL); fr=filter_system(sys,obj); assert fr.passed; assert any("C4" in r for r in fr.reasons_pass)
    def test_fail_wrong_category(self):
        fr=filter_system(make_system("Sys C3",[CorrosionCategory.C3],"High"),ObjectData(corrosion_category=CorrosionCategory.C5)); assert not fr.passed; assert any("C5" in r for r in fr.reasons_fail)
    def test_fail_low_durability(self): assert not filter_system(make_system("Sys Low",[CorrosionCategory.C4],"Low"),ObjectData(corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH)).passed
    def test_insufficient_data(self):
        sys=make_system("Empty",[],None); sys.layers=[]; fr=filter_system(sys,ObjectData(corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH),require_corrosion=True,require_durability=True); assert not fr.passed; assert fr.insufficient_data
    def test_temperature_fail(self):
        fr=filter_system(make_system("Temp",[CorrosionCategory.C3],"Medium",t_min=-20,t_max=40),ObjectData(corrosion_category=CorrosionCategory.C3,durability=DurabilityLevel.MEDIUM,temperature_min=-40,temperature_max=60)); assert not fr.passed
class TestScorer:
    def test_score_range(self):
        sys=make_system("Good",[CorrosionCategory.C4],"High"); obj=ObjectData(corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH); fr=filter_system(sys,obj); assert fr.passed; assert 0<=score_system(fr,obj).total<=100
    def test_higher_durability_better(self):
        obj=ObjectData(corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.MEDIUM); a=filter_system(make_system("Med",[CorrosionCategory.C4],"Medium"),obj); b=filter_system(make_system("High",[CorrosionCategory.C4],"High"),obj); assert score_system(b,obj).total>=score_system(a,obj).total
class TestRecommender:
    def test_recommend_ranking(self):
        systems=[make_system("C3 Medium",[CorrosionCategory.C3],"Medium"),make_system("C4 High",[CorrosionCategory.C4,CorrosionCategory.C5],"High"),make_system("C4 Medium",[CorrosionCategory.C4],"Medium"),make_system("C2 Low",[CorrosionCategory.C2],"Low")]; obj=ObjectData(object_name="Мост",corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.MEDIUM,surface_type=SurfaceType.NEW_STEEL,environment=EnvironmentType.OUTDOOR); result=RecommendationEngine().recommend(obj,systems,calculate_costs=False,top_n=5); assert len(result.items)>=1; assert result.items[0].score>=result.items[-1].score; assert "C2 Low" not in [i.system.system_name for i in result.items]; assert result.disclaimer
    def test_no_match(self):
        result=RecommendationEngine().recommend(ObjectData(corrosion_category=CorrosionCategory.C5,durability=DurabilityLevel.HIGH),[make_system("C1",[CorrosionCategory.C1],"Low")],calculate_costs=False); assert len(result.items)==0; assert result.message
    def test_empty_catalog(self):
        result=RecommendationEngine().recommend(ObjectData(),[],calculate_costs=False); assert result.insufficient_data; assert len(result.items)==0
    def test_report_format(self):
        obj=ObjectData(object_name="Резервуар",corrosion_category=CorrosionCategory.C4,durability=DurabilityLevel.HIGH); result=RecommendationEngine().recommend(obj,[make_system("C4 High",[CorrosionCategory.C4],"High")],calculate_costs=False); report=RecommendationEngine().format_report(result); assert "Подбор систем АКЗ" in report; assert "C4 High" in report; assert "Предварительный подбор" in report
