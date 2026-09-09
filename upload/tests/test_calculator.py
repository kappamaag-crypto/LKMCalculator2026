"""Тесты calculation engine."""
from __future__ import annotations
import pytest
from app.domain.models import Material,ObjectData
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
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,losses_percent=0.0,area_m2=1.0)
        assert result.wft==pytest.approx(200*100/73); assert result.theoretical_coverage==pytest.approx(10*73/200); assert result.practical_consumption_kg==pytest.approx(200/10/73*1.4); assert result.cost_per_m2==pytest.approx(result.practical_consumption_kg*552.0)

    def test_missing_density_blocks_engineering_calculation(self):
        material=make_primer(); material.density=None
        with pytest.raises(ValueError,match="Плотность материала"):
            LayerCalculator.calculate(material,target_dft=200.0,area_m2=1.0)

    def test_missing_volume_solids_blocks_engineering_calculation(self):
        material=make_primer(); material.solids_by_volume_percent=None
        with pytest.raises(ValueError,match="solids_by_volume_percent"):
            LayerCalculator.calculate(material,target_dft=200.0,area_m2=1.0)

    def test_invalid_volume_solids_over_100_blocks_engineering_calculation(self):
        material=make_primer(); material.solids_by_volume_percent=101.0
        with pytest.raises(ValueError,match="Объёмная доля сухого остатка"):
            LayerCalculator.calculate(material,target_dft=200.0,area_m2=1.0)

    def test_with_area(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,area_m2=100.0)
        assert result.total_consumption_kg==pytest.approx(result.practical_consumption_kg*100)
        assert result.total_consumption_l==pytest.approx(result.practical_consumption_l*100)
        assert result.total_cost==pytest.approx(result.cost_per_m2*100)

    def test_with_area_scales_thinner_separately(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,thinner_percent=5.0,thinner=make_thinner(),area_m2=100.0)
        assert result.total_consumption_l==pytest.approx(result.practical_consumption_l*100)
        assert result.thinner_consumption_l==pytest.approx(result.practical_consumption_l*0.05)
        assert result.thinner_consumption_kg==pytest.approx(result.thinner_consumption_l*0.9)
        assert result.total_cost==pytest.approx((result.cost_per_m2+result.thinner_cost_per_m2)*100)

    def test_consumption_only_no_procurement_fields(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,area_m2=1000.0)
        assert result.total_consumption_kg>0
        assert not hasattr(result,"packages_count"); assert not hasattr(result,"purchase_kg"); assert not hasattr(result,"remainder_kg")

    def test_with_thinner(self):
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,thinner_percent=5.0,thinner=make_thinner(),area_m2=1.0)
        assert result.thinner_consumption_l>0; assert result.thinner_consumption_kg>0; assert result.thinner_cost_per_m2>0

    def test_dilution_does_not_change_paint_volume_consumption(self):
        base=LayerCalculator.calculate(make_primer(),target_dft=200.0,area_m2=1.0)
        diluted=LayerCalculator.calculate(make_primer(),target_dft=200.0,thinner_percent=10.0,thinner=make_thinner(),area_m2=1.0)
        assert diluted.practical_consumption_l==pytest.approx(base.practical_consumption_l)
        assert diluted.practical_consumption_kg==pytest.approx(base.practical_consumption_kg)
        assert diluted.thinner_consumption_l>0
        assert diluted.wft>base.wft

    def test_thinner_without_price_keeps_physical_consumption(self):
        thinner=make_thinner(); thinner.price_per_kg=None
        result=LayerCalculator.calculate(make_primer(),target_dft=200.0,thinner_percent=5.0,thinner=thinner,area_m2=1.0)
        assert result.thinner_consumption_l>0; assert result.thinner_consumption_kg>0; assert result.thinner_cost_per_m2 is None; assert result.total_cost is None

    def test_price_per_liter_has_priority_when_consistent(self):
        material=make_primer(); material.price_per_liter=material.price_per_kg*material.density
        result=LayerCalculator.calculate(material,target_dft=200.0,area_m2=1.0)
        assert result.cost_per_m2==pytest.approx(result.practical_consumption_l*material.price_per_liter)

    def test_inconsistent_kg_and_liter_prices_are_rejected(self):
        with pytest.raises(ValueError,match="Цена за литр"):
            calculate_cost_by_price(0.1,0.14,552.0,900.0,density=1.4)

    def test_dilution_basis_paint_volume(self):
        wft=calculate_wft_with_dilution(200.0,73.0,thinner_percent=10.0,thinner_density=0.9,paint_density=1.4,basis=DILUTION_BASIS_BY_PAINT_VOLUME)
        assert wft==pytest.approx((200.0*100.0/73.0)*1.10)

    def test_dilution_basis_mass_uses_density_conversion(self):
        wft=calculate_wft_with_dilution(200.0,73.0,thinner_percent=10.0,thinner_density=0.9,paint_density=1.4,basis=DILUTION_BASIS_BY_MASS)
        expected=(200.0*100.0/73.0)*(1.0+0.10*1.4/0.9)
        assert wft==pytest.approx(expected)


class TestSystemCalculator:
    def test_two_layer_system(self):
        obj=ObjectData(object_name="Тест",area_m2=100.0); layers=[LayerInput(material=make_primer(),target_dft=200.0,losses_percent=0.0),LayerInput(material=make_finish(),target_dft=100.0,losses_percent=0.0)]; result,validation=SystemCalculator().calculate(obj,layers); assert not validation.has_errors; assert result.total_dft==300.0; assert len(result.layers)==2; assert result.total_cost_per_m2>0; assert result.total_cost==pytest.approx(result.total_cost_per_m2*100)

    def test_direct_area_is_sole_scaling_source(self):
        obj=ObjectData(area_m2=200.0); result,_=SystemCalculator().calculate(obj,[LayerInput(material=make_primer(),target_dft=200.0)])
        assert result.layers[0].total_consumption_kg==pytest.approx(result.layers[0].practical_consumption_kg*200); assert result.layers[0].total_consumption_l==pytest.approx(result.layers[0].practical_consumption_l*200)

    def test_missing_material_price_does_not_block_system_consumption(self):
        material=make_primer(); material.price_per_kg=None; material.price_per_liter=None
        obj=ObjectData(area_m2=100.0); result,validation=SystemCalculator().calculate(obj,[LayerInput(material=material,target_dft=200.0)])
        assert not validation.has_errors; assert result.total_practical_consumption_kg>0; assert result.total_practical_consumption_l>0; assert result.total_cost_per_m2 is None; assert result.total_cost is None

    def test_missing_critical_material_data_blocks_before_engine_calculation(self):
        material=make_primer(); material.solids_by_volume_percent=None
        obj=ObjectData(area_m2=100.0)
        result,validation=SystemCalculator().calculate(obj,[LayerInput(material=material,target_dft=200.0)])
        assert validation.has_errors
        assert any(i.code=="MAT_SOLIDS_UNKNOWN" for i in validation.errors)
        assert result.layers==[]


class TestValidation:
    def test_negative_area(self):
        r=validate_object_data(ObjectData(area_m2=-10)); assert r.has_errors; assert any(i.code=="OBJ_AREA_NEG" for i in r.errors)
    def test_dft_above_max(self):
        r=validate_layer_input(make_primer(),target_dft=250.0); assert r.has_warnings; assert any(i.code=="LAYER_DFT_ABOVE_MAX" for i in r.warnings)
    def test_solids_over_100(self):
        mat=make_primer(); mat.solids_by_volume_percent=120.0; r=validate_layer_input(mat,target_dft=100.0); assert r.has_errors; assert any(i.code=="MAT_SV_GT100" for i in r.errors)
    def test_losses_ge_100(self): assert validate_layer_input(make_primer(),target_dft=100.0,losses_percent=100.0).has_errors
    def test_dew_point(self):
        r=validate_object_data(ObjectData(area_m2=10,surface_temperature=5.0,dew_point=8.0)); assert r.has_errors; assert any(i.code=="OBJ_DEW_POINT" for i in r.errors)
    def test_before_calculation_blocks_on_error(self):
        mat=make_primer(); mat.density=-1.0; assert validate_before_calculation(ObjectData(area_m2=10),[(mat,200.0,0.0,0.0)]).has_errors
