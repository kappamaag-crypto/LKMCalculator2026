"""Тесты calculation engine."""
from __future__ import annotations
import pytest
from app.domain.models import Material,ObjectData
from app.domain.enums import MaterialType,BinderType
from app.domain.calculator import LayerCalculator,SystemCalculator,LayerInput
from app.domain.validation import validate_layer_input,validate_object_data,validate_before_calculation

def make_primer()->Material:
    return Material(id=1,manufacturer="Blank",brand="Blank",material_name="Грунт-Эмаль Blank Universal",material_type=MaterialType.PRIMER_ENAMEL,binder_type=BinderType.EPOXY,density=1.4,solids_percent=73.0,price_per_kg=552.0,recommended_dft_min=100,recommended_dft_max=200,packaging_kg=20.0)
def make_finish()->Material:
    return Material(id=2,manufacturer="Blank",brand="Blank",material_name="Эмаль Blank Finish",material_type=MaterialType.FINISH,binder_type=BinderType.POLYURETHANE,density=1.3,solids_percent=58.0,price_per_kg=892.0,recommended_dft_min=60,recommended_dft_max=100,packaging_kg=20.0)
def make_thinner()->Material:
    return Material(id=3,material_name="Разбавитель для грунта",material_type=MaterialType.THINNER,density=0.9,solids_percent=0.0,price_per_kg=100.0)
class TestLayerCalculator:
    def test_primer_basic(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,losses_percent=0.0,area_m2=1.0)
        assert result.wft==pytest.approx(200*100/73); assert result.theoretical_coverage==pytest.approx(10*73/200); assert result.practical_consumption_kg==pytest.approx(200/10/73*1.4); assert result.cost_per_m2==pytest.approx(result.practical_consumption_kg*552.0)
    def test_with_area(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,area_m2=100.0); assert result.total_consumption_kg==pytest.approx(result.practical_consumption_kg*100); assert result.total_cost==pytest.approx(result.cost_per_m2*100)
    def test_consumption_only_no_procurement_fields(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,area_m2=1000.0)
        assert result.total_consumption_kg>0
        assert not hasattr(result,"packages_count"); assert not hasattr(result,"purchase_kg"); assert not hasattr(result,"remainder_kg")
    def test_with_thinner(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,thinner_percent=5.0,thinner=make_thinner(),area_m2=1.0); assert result.thinner_consumption_l>0; assert result.thinner_consumption_kg>0; assert result.thinner_cost_per_m2>0
class TestSystemCalculator:
    def test_two_layer_system(self):
        obj=ObjectData(object_name="Тест",area_m2=100.0); layers=[LayerInput(material=make_primer(),target_dft=200.0,losses_percent=0.0),LayerInput(material=make_finish(),target_dft=100.0,losses_percent=0.0)]; result,validation=SystemCalculator().calculate(obj,layers); assert not validation.has_errors; assert result.total_dft==300.0; assert len(result.layers)==2; assert result.total_cost_per_m2>0; assert result.total_cost==pytest.approx(result.total_cost_per_m2*100)
    def test_area_from_elements(self):
        obj=ObjectData(area_per_element=50.0,elements_count=4); result,_=SystemCalculator().calculate(obj,[LayerInput(material=make_primer(),target_dft=200.0)]); assert result.layers[0].total_consumption_kg==pytest.approx(result.layers[0].practical_consumption_kg*200)
class TestValidation:
    def test_negative_area(self):
        r=validate_object_data(ObjectData(area_m2=-10)); assert r.has_errors; assert any(i.code=="OBJ_AREA_NEG" for i in r.errors)
    def test_dft_above_max(self):
        r=validate_layer_input(make_primer(),target_dft=250.0); assert r.has_warnings; assert any(i.code=="LAYER_DFT_ABOVE_MAX" for i in r.warnings)
    def test_solids_over_100(self):
        mat=make_primer(); mat.solids_percent=120.0; r=validate_layer_input(mat,target_dft=100.0); assert r.has_errors; assert any(i.code=="MAT_SOLIDS_GT100" for i in r.errors)
    def test_losses_ge_100(self): assert validate_layer_input(make_primer(),target_dft=100.0,losses_percent=100.0).has_errors
    def test_dew_point(self):
        r=validate_object_data(ObjectData(area_m2=10,surface_temperature=5.0,dew_point=8.0)); assert r.has_errors; assert any(i.code=="OBJ_DEW_POINT" for i in r.errors)
    def test_before_calculation_blocks_on_error(self):
        mat=make_primer(); mat.density=-1.0; assert validate_before_calculation(ObjectData(area_m2=10),[(mat,200.0,0.0,0.0)]).has_errors
class TestComparison:
    def test_compare_two_systems(self):
        from app.domain.comparison import ComparisonEngine
        primer,finish,obj=make_primer(),make_finish(),ObjectData(area_m2=100.0); comparison=ComparisonEngine().compare(obj,[("Система А",[LayerInput(material=primer,target_dft=200.0),LayerInput(material=finish,target_dft=100.0)]),("Система Б",[LayerInput(material=primer,target_dft=150.0),LayerInput(material=finish,target_dft=80.0)])]); assert len(comparison.systems)==2; assert comparison.cheapest_index is not None; assert comparison.thinnest_index is not None; assert comparison.best_balance_index is not None; table=ComparisonEngine().to_table(comparison); assert len(table)>=5; assert table[0]["indicator"]=="Название"
