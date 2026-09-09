"""Unit-тесты расчётных формул v3.0."""
from __future__ import annotations
import pytest
from app.domain.formulas import (DILUTION_BASIS_BY_MASS,DILUTION_BASIS_BY_MIX_VOLUME,calculate_wft,calculate_theoretical_coverage,calculate_loss_coefficient,calculate_practical_coverage,calculate_thinner,calculate_layer,LayerCalcInput,scale_to_area,total_area)

class TestBasicFormulas:
    def test_wft_primer(self): assert calculate_wft(200.0,73.0)==pytest.approx(200*100/73)
    def test_wft_finish(self): assert calculate_wft(100.0,58.0)==pytest.approx(100*100/58)
    def test_wft_zero_inputs(self): assert calculate_wft(0,73)==0.0 and calculate_wft(200,0)==0.0
    def test_theoretical_coverage(self):
        wft=calculate_wft(200.0,73.0); assert calculate_theoretical_coverage(wft)==pytest.approx(1000.0/wft)
    def test_loss_coefficient(self):
        assert calculate_loss_coefficient(0)==1.0
        assert calculate_loss_coefficient(20)==pytest.approx(100/80)
    @pytest.mark.parametrize("losses",[-0.01,100.0,100.01])
    def test_loss_coefficient_rejects_invalid_values(self,losses):
        with pytest.raises(ValueError): calculate_loss_coefficient(losses)
    def test_practical_coverage(self): assert calculate_practical_coverage(10.0,1.25)==pytest.approx(8.0)
    def test_consumption_and_cost(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0,price_per_kg=552.0))
        assert r.wft==pytest.approx(200*100/73); assert r.theoretical_coverage==pytest.approx(1000/r.wft); assert r.practical_consumption_l==pytest.approx(r.wft/1000); assert r.practical_consumption_kg==pytest.approx(r.practical_consumption_l*1.4); assert r.cost_per_m2==pytest.approx(r.practical_consumption_kg*552)
    def test_unknown_material_price_does_not_block_consumption(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0)); assert r.practical_consumption_l>0 and r.practical_consumption_kg>0 and r.cost_per_m2 is None
    def test_price_per_liter_has_priority_when_both_prices_match_density(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0,price_per_kg=552.0,price_per_liter=772.8)); assert r.cost_per_m2==pytest.approx(r.practical_consumption_l*772.8)
    def test_price_per_liter_allows_small_density_rounding_difference(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0,price_per_kg=552.0,price_per_liter=800.0)); assert r.cost_per_m2==pytest.approx(r.practical_consumption_l*800.0)
    def test_price_per_liter_rejects_inconsistent_price_via_density(self):
        with pytest.raises(ValueError,match="не соответствует цене за кг"): calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0,price_per_kg=552.0,price_per_liter=950.0))
    def test_with_losses(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73.0,dry_thickness=200.0,losses_percent=20.0,price_per_kg=552.0)); k=100/80; assert r.loss_coefficient==pytest.approx(k); assert r.practical_coverage==pytest.approx(r.theoretical_coverage/k); assert r.practical_consumption_kg>r.theoretical_consumption_kg
    def test_thinner(self):
        l,kg,c=calculate_thinner(.274,5,.9,100); assert l==pytest.approx(.274*.05); assert kg==pytest.approx(.274*.05*.9); assert c==pytest.approx(.274*.05*.9*100)
    def test_thinner_without_price_still_calculates_consumption(self):
        l,kg,c=calculate_thinner(.274,5,.9,None); assert l==pytest.approx(.274*.05); assert kg==pytest.approx(.274*.05*.9); assert c is None
    def test_thinner_by_mix_volume(self):
        l,kg,_=calculate_thinner(1,10,.8,100,DILUTION_BASIS_BY_MIX_VOLUME); assert l==pytest.approx(.1/.9); assert kg==pytest.approx(l*.8)
    def test_thinner_by_mass(self):
        l,kg,_=calculate_thinner(1,10,.8,100,DILUTION_BASIS_BY_MASS,parent_density=1.4); assert kg==pytest.approx(.14); assert l==pytest.approx(kg/.8)
    def test_dilution_changes_wft_but_not_paint_consumption_basis(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=70,dry_thickness=100,price_per_kg=500,thinner_percent=10)); assert r.wft==pytest.approx((100/.70)*1.1); assert r.theoretical_consumption_l==pytest.approx(100/.70/1000); assert r.thinner_consumption_l==pytest.approx(r.practical_consumption_l*.1)
    def test_dilution_cost_is_material_plus_thinner_when_both_prices_known(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=70,dry_thickness=100,price_per_kg=500,thinner_percent=10,thinner_density=.8,thinner_price_per_kg=100)); assert r.cost_per_m2==pytest.approx(r.practical_consumption_kg*500); assert r.thinner_cost_per_m2==pytest.approx(r.thinner_consumption_kg*100)
    def test_unknown_thinner_price_does_not_zero_or_hide_thinner_consumption(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=70,dry_thickness=100,price_per_kg=500,thinner_percent=10,thinner_density=.8)); assert r.cost_per_m2 is not None and r.thinner_consumption_l>0 and r.thinner_consumption_kg>0 and r.thinner_cost_per_m2 is None
    def test_scale_to_area(self): assert scale_to_area(.5,100)==50 and scale_to_area(.5,0)==0
    def test_total_area_legacy_compatibility(self): assert total_area(1250,5)==6250 and total_area(0,5)==0

class TestExcelConsistency:
    def test_primer_excel_row7(self):
        r=calculate_layer(LayerCalcInput(density=1.4,solids_by_volume_percent=73,dry_thickness=200,price_per_kg=552)); assert r.wft==pytest.approx(200*100/73); assert r.theoretical_coverage==pytest.approx(10*73/200); assert r.theoretical_consumption_l==pytest.approx(200/10/73); assert r.theoretical_consumption_kg==pytest.approx(200/10/73*1.4)
    def test_finish_excel_row8(self):
        r=calculate_layer(LayerCalcInput(density=1.3,solids_by_volume_percent=58,dry_thickness=100,price_per_kg=892)); assert r.wft==pytest.approx(100*100/58); assert r.theoretical_coverage==pytest.approx(10*58/100); assert r.theoretical_consumption_l==pytest.approx(100/10/58); assert r.theoretical_consumption_kg==pytest.approx(100/10/58*1.3)
