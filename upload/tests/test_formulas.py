"""Unit-тесты расчётных формул v3.0."""

from __future__ import annotations

import pytest

from app.domain.formulas import (
    DILUTION_BASIS_BY_MASS,
    DILUTION_BASIS_BY_MIX_VOLUME,
    calculate_wft,
    calculate_theoretical_coverage,
    calculate_loss_coefficient,
    calculate_practical_coverage,
    calculate_thinner,
    calculate_layer,
    LayerCalcInput,
    scale_to_area,
    total_area,
)


class TestBasicFormulas:
    def test_wft_primer(self):
        assert calculate_wft(200.0, 73.0) == pytest.approx(200 * 100 / 73)

    def test_wft_finish(self):
        assert calculate_wft(100.0, 58.0) == pytest.approx(100 * 100 / 58)

    def test_wft_zero_inputs(self):
        assert calculate_wft(0, 73) == 0.0
        assert calculate_wft(200, 0) == 0.0

    def test_theoretical_coverage(self):
        wft = calculate_wft(200.0, 73.0)
        assert calculate_theoretical_coverage(wft) == pytest.approx(1000.0 / wft)

    def test_loss_coefficient(self):
        assert calculate_loss_coefficient(0) == 1.0
        assert calculate_loss_coefficient(20) == pytest.approx(100 / 80)
        assert calculate_loss_coefficient(100) == 1.0
        assert calculate_loss_coefficient(-5) == 1.0

    def test_practical_coverage(self):
        assert calculate_practical_coverage(10.0, 1.25) == pytest.approx(8.0)

    def test_consumption_and_cost(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, price_per_kg=552.0))
        assert result.wft == pytest.approx(200 * 100 / 73)
        assert result.theoretical_coverage == pytest.approx(1000 / result.wft)
        assert result.practical_coverage == pytest.approx(result.theoretical_coverage)
        assert result.theoretical_consumption_l == pytest.approx(result.wft / 1000)
        assert result.theoretical_consumption_kg == pytest.approx(result.theoretical_consumption_l * 1.4)
        assert result.cost_per_m2 == pytest.approx(result.practical_consumption_kg * 552.0)

    def test_unknown_material_price_does_not_block_consumption(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0))
        assert result.practical_consumption_l > 0
        assert result.practical_consumption_kg > 0
        assert result.cost_per_m2 is None

    def test_price_per_liter_has_priority_when_both_prices_match_density(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, price_per_kg=552.0, price_per_liter=772.8))
        assert result.cost_per_m2 == pytest.approx(result.practical_consumption_l * 772.8)

    def test_price_per_liter_allows_small_density_rounding_difference(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, price_per_kg=552.0, price_per_liter=800.0))
        assert result.cost_per_m2 == pytest.approx(result.practical_consumption_l * 800.0)

    def test_price_per_liter_rejects_inconsistent_price_via_density(self):
        with pytest.raises(ValueError, match="не соответствует цене за кг"):
            calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, price_per_kg=552.0, price_per_liter=950.0))

    def test_with_losses(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, losses_percent=20.0, price_per_kg=552.0))
        k = 100 / 80
        assert result.loss_coefficient == pytest.approx(k)
        assert result.practical_coverage == pytest.approx(result.theoretical_coverage / k)
        assert result.practical_consumption_kg > result.theoretical_consumption_kg

    def test_thinner(self):
        thinner_l, thinner_kg, cost = calculate_thinner(0.274, 5.0, 0.9, 100.0)
        assert thinner_l == pytest.approx(0.274 * 0.05)
        assert thinner_kg == pytest.approx(0.274 * 0.05 * 0.9)
        assert cost == pytest.approx(0.274 * 0.05 * 0.9 * 100)

    def test_thinner_without_price_still_calculates_consumption(self):
        thinner_l, thinner_kg, cost = calculate_thinner(0.274, 5.0, 0.9, None)
        assert thinner_l == pytest.approx(0.274 * 0.05)
        assert thinner_kg == pytest.approx(0.274 * 0.05 * 0.9)
        assert cost is None

    def test_thinner_by_mix_volume(self):
        thinner_l, thinner_kg, _ = calculate_thinner(1.0, 10.0, 0.8, 100.0, DILUTION_BASIS_BY_MIX_VOLUME)
        assert thinner_l == pytest.approx(1.0 * 0.10 / 0.90)
        assert thinner_kg == pytest.approx(thinner_l * 0.8)

    def test_thinner_by_mass(self):
        thinner_l, thinner_kg, _ = calculate_thinner(1.0, 10.0, 0.8, 100.0, DILUTION_BASIS_BY_MASS, parent_density=1.4)
        assert thinner_kg == pytest.approx(1.4 * 0.10)
        assert thinner_l == pytest.approx(thinner_kg / 0.8)

    def test_dilution_changes_wft_but_not_paint_consumption_basis(self):
        result = calculate_layer(LayerCalcInput(density=1.4, solids_percent=70.0, dry_thickness=100.0, price_per_kg=500.0, thinner_percent=10.0))
        assert result.wft == pytest.approx((100 / 0.70) * 1.10)
        assert result.theoretical_consumption_l == pytest.approx(100 / 0.70 / 1000)
        assert result.thinner_consumption_l == pytest.approx(result.practical_consumption_l * 0.10)

    def test_dilution_cost_is_material_plus_thinner_when_both_prices_known(self):
        result = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_percent=70.0,
                dry_thickness=100.0,
                price_per_kg=500.0,
                thinner_percent=10.0,
                thinner_density=0.8,
                thinner_price_per_kg=100.0,
            )
        )
        expected_material = result.practical_consumption_kg * 500.0
        expected_thinner = result.thinner_consumption_kg * 100.0
        assert result.cost_per_m2 == pytest.approx(expected_material)
        assert result.thinner_cost_per_m2 == pytest.approx(expected_thinner)
        assert result.cost_per_m2 + result.thinner_cost_per_m2 == pytest.approx(expected_material + expected_thinner)

    def test_unknown_thinner_price_does_not_zero_or_hide_thinner_consumption(self):
        result = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_percent=70.0,
                dry_thickness=100.0,
                price_per_kg=500.0,
                thinner_percent=10.0,
                thinner_density=0.8,
                thinner_price_per_kg=None,
            )
        )
        assert result.cost_per_m2 is not None
        assert result.thinner_consumption_l > 0
        assert result.thinner_consumption_kg > 0
        assert result.thinner_cost_per_m2 is None

    def test_scale_to_area(self):
        assert scale_to_area(0.5, 100) == 50.0
        assert scale_to_area(0.5, 0) == 0.0

    def test_total_area(self):
        assert total_area(1250.0, 5) == 6250.0
        assert total_area(0, 5) == 0.0


class TestExcelConsistency:
    def test_primer_excel_row7(self):
        r = calculate_layer(LayerCalcInput(density=1.4, solids_percent=73.0, dry_thickness=200.0, price_per_kg=552.0))
        assert r.wft == pytest.approx(200 * 100 / 73)
        assert r.theoretical_coverage == pytest.approx(10 * 73 / 200)
        assert r.theoretical_consumption_l == pytest.approx(200 / 10 / 73)
        assert r.theoretical_consumption_kg == pytest.approx(200 / 10 / 73 * 1.4)

    def test_finish_excel_row8(self):
        r = calculate_layer(LayerCalcInput(density=1.3, solids_percent=58.0, dry_thickness=100.0, price_per_kg=892.0))
        assert r.wft == pytest.approx(100 * 100 / 58)
        assert r.theoretical_coverage == pytest.approx(10 * 58 / 100)
        assert r.theoretical_consumption_l == pytest.approx(100 / 10 / 58)
        assert r.theoretical_consumption_kg == pytest.approx(100 / 10 / 58 * 1.3)
