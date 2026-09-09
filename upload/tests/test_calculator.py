"""Тесты calculation engine."""
from __future__ import annotations
import pytest
from app.domain.models import Material,ObjectData,CoatingSystem,LayerDefinition
from app.domain.enums import MaterialType,BinderType
from app.domain.calculator import LayerCalculator,SystemCalculator,LayerInput
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME,DILUTION_BASIS_BY_MASS,calculate_cost_by_price,calculate_wft_with_dilution
from app.domain.validation import validate_layer_input,validate_object_data,validate_before_calculation

def make_primer()->Material:
    return Material(id=1,manufacturer="Blank",brand="Blank",material_name="Грунт-Эмаль Blank Universal",material_type=MaterialType.PRIMER_ENAMEL,binder_type=BinderType.EPOXY,density=1.4,solids_percent=73.0,solids_by_volume_percent=73.0,price_per_kg=552.0,recommended_dft_min=100,recommended_dft_max=200,packaging_kg=20.0)
def make_finish()->Material:
    return Material(id=2,manufacturer="Blank",brand="Blank",material_name="Эмаль Blank Finish",material_type=MaterialType.FINISH,binder_type=BinderType.POLYURETHANE,density=1.3,solids_percent=58.0,solids_by_volume_percent=58.0,price_per_kg=892.0,recommended_dft_min=60,recommended_dft_max=100,packaging_kg=20.0)
def make_thinner()->Material:
    return Material(id=3,material_name="Разбавитель для грунта",material_type=MaterialType.THINNER,density=0.9,solids_percent=0.0,price_per_kg=100.0)
class TestLayerCalculator:
    def test_primer_basic(self):
        r=LayerCalculator.calculate(make_primer(),200,area_m2=1); assert r.wft==pytest.approx(200*100/73); assert r.practical_consumption_kg==pytest.approx(200/10/73*1.4); assert r.cost_per_m2==pytest.approx(r.practical_consumption_kg*552)
    def test_missing_density_blocks_engineering_calculation(self):
        m=make_primer(); m.density=None
        with pytest.raises(ValueError,match="Плотность материала"): LayerCalculator.calculate(m,200)
    def test_missing_volume_solids_blocks_engineering_calculation(self):
        m=make_primer(); m.solids_by_volume_percent=None
        with pytest.raises(ValueError,match="solids_by_volume_percent"): LayerCalculator.calculate(m,200)
    def test_invalid_volume_solids_over_100_blocks_engineering_calculation(self):
        m=make_primer(); m.solids_by_volume_percent=101
        with pytest.raises(ValueError,match="Объёмная доля сухого остатка"): LayerCalculator.calculate(m,200)
    def test_with_area(self):
        r=LayerCalculator.calculate(make_primer(),200,area_m2=100); assert r.total_consumption_kg==pytest.approx(r.practical_consumption_kg*100); assert r.total_cost==pytest.approx(r.cost_per_m2*100)
    def test_with_area_scales_thinner_separately(self):
        r=LayerCalculator.calculate(make_primer(),200,thinner_percent=5,thinner=make_thinner(),area_m2=100); assert r.thinner_consumption_l==pytest.approx(r.practical_consumption_l*.05); assert r.total_cost==pytest.approx((r.cost_per_m2+r.thinner_cost_per_m2)*100)
    def test_consumption_only_no_procurement_fields(self):
        r=LayerCalculator.calculate(make_primer(),200,area_m2=1000); assert r.total_consumption_kg>0; assert not hasattr(r,"packages_count") and not hasattr(r,"purchase_kg") and not hasattr(r,"remainder_kg")
    def test_with_thinner(self): assert LayerCalculator.calculate(make_primer(),200,thinner_percent=5,thinner=make_thinner()).thinner_consumption_l>0
    def test_dilution_does_not_change_paint_volume_consumption(self):
        base=LayerCalculator.calculate(make_primer(),200); diluted=LayerCalculator.calculate(make_primer(),200,10,thinner=make_thinner()); assert diluted.practical_consumption_l==pytest.approx(base.practical_consumption_l); assert diluted.wft>base.wft
    def test_thinner_without_price_keeps_physical_consumption(self):
        t=make_thinner(); t.price_per_kg=None; r=LayerCalculator.calculate(make_primer(),200,5,t,1); assert r.thinner_consumption_l>0 and r.thinner_cost_per_m2 is None and r.total_cost is None
    def test_price_per_liter_has_priority_when_consistent(self):
        m=make_primer(); m.price_per_liter=m.price_per_kg*m.density; r=LayerCalculator.calculate(m,200); assert r.cost_per_m2==pytest.approx(r.practical_consumption_l*m.price_per_liter)
    def test_inconsistent_kg_and_liter_prices_are_rejected(self):
        with pytest.raises(ValueError,match="Цена за литр"): calculate_cost_by_price(.1,.14,552,900,density=1.4)
    def test_dilution_basis_paint_volume(self): assert calculate_wft_with_dilution(200,73,10,.9,1.4,DILUTION_BASIS_BY_PAINT_VOLUME)==pytest.approx((200*100/73)*1.1)
    def test_dilution_basis_mass_uses_density_conversion(self): assert calculate_wft_with_dilution(200,73,10,.9,1.4,DILUTION_BASIS_BY_MASS)==pytest.approx((200*100/73)*(1+.1*1.4/.9))
class TestSystemCalculator:
    def test_two_layer_system(self):
        obj=ObjectData(area_m2=100); result,v=SystemCalculator().calculate(obj,[LayerInput(make_primer(),200),LayerInput(make_finish(),100)]); assert not v.has_errors and result.total_dft==300 and result.total_cost_per_m2>0
    def test_direct_area_is_sole_scaling_source(self):
        r,_=SystemCalculator().calculate(ObjectData(area_m2=200),[LayerInput(make_primer(),200)]); assert r.layers[0].total_consumption_kg==pytest.approx(r.layers[0].practical_consumption_kg*200)
    def test_missing_material_price_does_not_block_system_consumption(self):
        m=make_primer(); m.price_per_kg=None; m.price_per_liter=None; r,v=SystemCalculator().calculate(ObjectData(area_m2=100),[LayerInput(m,200)]); assert not v.has_errors and r.total_practical_consumption_kg>0 and r.total_cost_per_m2 is None
    def test_missing_critical_material_data_blocks_before_engine_calculation(self):
        m=make_primer(); m.solids_by_volume_percent=None; r,v=SystemCalculator().calculate(ObjectData(area_m2=100),[LayerInput(m,200)]); assert v.has_errors and any(i.code=="MAT_SOLIDS_UNKNOWN" for i in v.errors) and r.layers==[]
    def test_missing_system_layer_material_never_calculates_partial_system(self):
        system=CoatingSystem(system_name="Incomplete",layers=[LayerDefinition(layer_number=1,material=make_primer(),target_dft=100),LayerDefinition(layer_number=2,material=None,material_id=999,target_dft=80)],number_of_layers=2)
        r,v=SystemCalculator().calculate_from_system(ObjectData(area_m2=10),system,{1:make_primer()}); assert v.has_errors and any(i.code=="SYSTEM_LAYER_MATERIAL_MISSING" for i in v.errors) and r.layers==[]
class TestValidation:
    def test_negative_area(self): assert validate_object_data(ObjectData(area_m2=-10)).has_errors
    def test_dft_above_max(self): assert validate_layer_input(make_primer(),250).has_warnings
    def test_solids_over_100(self):
        m=make_primer(); m.solids_by_volume_percent=120; assert validate_layer_input(m,100).has_errors
    def test_losses_ge_100(self): assert validate_layer_input(make_primer(),100,100).has_errors
    def test_dew_point(self): assert validate_object_data(ObjectData(area_m2=10,surface_temperature=5,dew_point=8)).has_errors
    def test_before_calculation_blocks_on_error(self):
        m=make_primer(); m.density=-1; assert validate_before_calculation(ObjectData(area_m2=10),[(m,200,0,0)]).has_errors
