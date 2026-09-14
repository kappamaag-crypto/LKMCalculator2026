"""Unit-тесты расчётных формул v3.0."""
from __future__ import annotations

import pytest

from app.domain.formulas import (
    DILUTION_BASIS_BY_COMPONENT_VOLUME,
    DILUTION_BASIS_BY_MASS,
    DILUTION_BASIS_BY_MIX_VOLUME,
    DILUTION_BASIS_BY_PAINT_VOLUME,
    LayerCalcInput,
    calculate_layer,
    calculate_loss_coefficient,
    calculate_practical_coverage,
    calculate_theoretical_coverage,
    calculate_thinner,
    calculate_wft,
    scale_to_area,
    total_area,
)


class TestBasicFormulas:
    def test_wft_primer(self):
        assert calculate_wft(200.0, 73.0) == pytest.approx(200 * 100 / 73)

    def test_wft_finish(self):
        assert calculate_wft(100.0, 58.0) == pytest.approx(100 * 100 / 58)

    def test_wft_zero_inputs(self):
        assert calculate_wft(0, 73) == 0.0 and calculate_wft(200, 0) == 0.0

    def test_theoretical_coverage(self):
        wft = calculate_wft(200.0, 73.0)
        assert calculate_theoretical_coverage(wft) == pytest.approx(1000.0 / wft)

    def test_loss_coefficient(self):
        assert calculate_loss_coefficient(0) == 1.0
        assert calculate_loss_coefficient(20) == pytest.approx(100 / 80)

    @pytest.mark.parametrize("losses", [-0.01, 100.0, 100.01])
    def test_loss_coefficient_rejects_invalid_values(self, losses):
        with pytest.raises(ValueError):
            calculate_loss_coefficient(losses)

    def test_practical_coverage(self):
        assert calculate_practical_coverage(10.0, 1.25) == pytest.approx(8.0)

    def test_consumption_and_cost(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=73.0,
                dry_thickness=200.0,
                price_per_kg=552.0,
            )
        )
        assert r.wft == pytest.approx(200 * 100 / 73)
        assert r.theoretical_coverage == pytest.approx(1000 / r.wft)
        assert r.practical_consumption_l == pytest.approx(r.wft / 1000)
        assert r.practical_consumption_kg == pytest.approx(r.practical_consumption_l * 1.4)
        assert r.cost_per_m2 == pytest.approx(r.practical_consumption_kg * 552)

    def test_unknown_material_price_does_not_block_consumption(self):
        r = calculate_layer(
            LayerCalcInput(density=1.4, solids_by_volume_percent=73.0, dry_thickness=200.0)
        )
        assert r.practical_consumption_l > 0
        assert r.practical_consumption_kg > 0
        assert r.cost_per_m2 is None

    def test_price_per_liter_has_priority_when_both_prices_match_density(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=73.0,
                dry_thickness=200.0,
                price_per_kg=552.0,
                price_per_liter=772.8,
            )
        )
        assert r.cost_per_m2 == pytest.approx(r.practical_consumption_l * 772.8)

    def test_price_per_liter_allows_small_density_rounding_difference(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=73.0,
                dry_thickness=200.0,
                price_per_kg=552.0,
                price_per_liter=800.0,
            )
        )
        assert r.cost_per_m2 == pytest.approx(r.practical_consumption_l * 800.0)

    def test_price_per_liter_rejects_inconsistent_price_via_density(self):
        with pytest.raises(ValueError, match="не соответствует цене за кг"):
            calculate_layer(
                LayerCalcInput(
                    density=1.4,
                    solids_by_volume_percent=73.0,
                    dry_thickness=200.0,
                    price_per_kg=552.0,
                    price_per_liter=950.0,
                )
            )

    def test_with_losses(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=73.0,
                dry_thickness=200.0,
                losses_percent=20.0,
                price_per_kg=552.0,
            )
        )
        k = 100 / 80
        assert r.loss_coefficient == pytest.approx(k)
        assert r.practical_coverage == pytest.approx(r.theoretical_coverage / k)
        assert r.practical_consumption_kg > r.theoretical_consumption_kg

    def test_thinner(self):
        l, kg, c = calculate_thinner(
            0.274, 5, 0.9, 100, DILUTION_BASIS_BY_PAINT_VOLUME, 1.4
        )
        assert l == pytest.approx(0.274 * 0.05)
        assert kg == pytest.approx(0.274 * 0.05 * 0.9)
        assert c == pytest.approx(0.274 * 0.05 * 0.9 * 100)

    def test_thinner_without_price_still_calculates_consumption(self):
        l, kg, c = calculate_thinner(
            0.274, 5, 0.9, None, DILUTION_BASIS_BY_PAINT_VOLUME, 1.4
        )
        assert l == pytest.approx(0.274 * 0.05)
        assert kg == pytest.approx(0.274 * 0.05 * 0.9)
        assert c is None

    def test_thinner_by_mix_volume(self):
        l, kg, _ = calculate_thinner(
            1, 10, 0.8, 100, DILUTION_BASIS_BY_MIX_VOLUME, 1.4
        )
        assert l == pytest.approx(0.1 / 0.9)
        assert kg == pytest.approx(l * 0.8)

    def test_thinner_by_mass(self):
        l, kg, _ = calculate_thinner(
            1, 10, 0.8, 100, DILUTION_BASIS_BY_MASS, 1.4
        )
        assert kg == pytest.approx(0.14)
        assert l == pytest.approx(kg / 0.8)

    def test_thinner_by_component_volume(self):
        l, kg, _ = calculate_thinner(
            1, 10, 0.8, 100, DILUTION_BASIS_BY_COMPONENT_VOLUME, 1.4
        )
        assert l == pytest.approx(0.1)
        assert kg == pytest.approx(0.08)

    def test_dilution_changes_wft_but_not_paint_consumption_basis(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=70,
                dry_thickness=100,
                price_per_kg=500,
                thinner_percent=10,
                thinner_density=0.8,
                thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME,
            )
        )
        assert r.wft == pytest.approx((100 / 0.70) * 1.1)
        assert r.theoretical_consumption_l == pytest.approx(100 / 0.70 / 1000)
        assert r.thinner_consumption_l == pytest.approx(r.practical_consumption_l * 0.1)

    def test_dilution_cost_is_material_plus_thinner_when_both_prices_known(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=70,
                dry_thickness=100,
                price_per_kg=500,
                thinner_percent=10,
                thinner_density=0.8,
                thinner_price_per_kg=100,
                thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME,
            )
        )
        assert r.cost_per_m2 == pytest.approx(r.practical_consumption_kg * 500)
        assert r.thinner_cost_per_m2 == pytest.approx(r.thinner_consumption_kg * 100)

    def test_unknown_thinner_price_does_not_zero_or_hide_thinner_consumption(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.4,
                solids_by_volume_percent=70,
                dry_thickness=100,
                price_per_kg=500,
                thinner_percent=10,
                thinner_density=0.8,
                thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME,
            )
        )
        assert r.cost_per_m2 is not None
        assert r.thinner_consumption_l > 0
        assert r.thinner_consumption_kg > 0
        assert r.thinner_cost_per_m2 is None

    def test_unknown_thinner_density_is_not_replaced_by_one(self):
        with pytest.raises(ValueError, match="плотност.*разбавител"):
            calculate_thinner(
                1.0,
                10.0,
                None,
                None,
                DILUTION_BASIS_BY_PAINT_VOLUME,
                1.4,
            )

    def test_unknown_parent_density_is_not_replaced_by_one_for_mass_basis(self):
        with pytest.raises(ValueError, match="Плотность ЛКМ"):
            calculate_thinner(
                1.0,
                10.0,
                0.8,
                None,
                DILUTION_BASIS_BY_MASS,
                None,
            )

    def test_unknown_dilution_basis_is_not_replaced_by_paint_volume(self):
        with pytest.raises(ValueError, match="основание дозирования"):
            calculate_thinner(1.0, 10.0, 0.8, None, None, 1.4)

    def test_zero_dilution_does_not_require_thinner_engineering_data(self):
        l, kg, c = calculate_thinner(1.0, 0.0, None, None, None, None)
        assert l == 0.0
        assert kg == 0.0
        assert c == 0.0

    def test_calculate_layer_rejects_unknown_thinner_data(self):
        with pytest.raises(ValueError, match="плотност.*разбавител"):
            calculate_layer(
                LayerCalcInput(
                    density=1.4,
                    solids_by_volume_percent=70.0,
                    dry_thickness=100.0,
                    thinner_percent=10.0,
                    thinner_density=None,
                    thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME,
                )
            )

    def test_calculate_layer_rejects_unknown_dilution_basis(self):
        with pytest.raises(ValueError, match="основание дозирования"):
            calculate_layer(
                LayerCalcInput(
                    density=1.4,
                    solids_by_volume_percent=70.0,
                    dry_thickness=100.0,
                    thinner_percent=10.0,
                    thinner_density=0.8,
                    thinner_basis=None,
                )
            )

    def test_scale_to_area(self):
        assert scale_to_area(0.5, 100) == 50 and scale_to_area(0.5, 0) == 0

    def test_total_area_legacy_compatibility(self):
        assert total_area(1250, 5) == 6250 and total_area(0, 5) == 0

    def test_precision_is_not_truncated_between_formula_steps(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.37,
                solids_by_volume_percent=67.3,
                dry_thickness=137.5,
                losses_percent=7.25,
            )
        )
        expected_l = (137.5 / 67.3 * 100.0) / 1000.0 * (100.0 / (100.0 - 7.25))
        expected_kg = expected_l * 1.37
        assert r.practical_consumption_l == pytest.approx(expected_l, rel=1e-12, abs=1e-15)
        assert r.practical_consumption_kg == pytest.approx(expected_kg, rel=1e-12, abs=1e-15)
        assert r.practical_consumption_l != pytest.approx(round(r.practical_consumption_l, 3), rel=0, abs=1e-15)

    def test_kg_l_unit_invariant(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.63,
                solids_by_volume_percent=64.7,
                dry_thickness=250.0,
                losses_percent=11.0,
            )
        )
        assert r.theoretical_consumption_kg == pytest.approx(r.theoretical_consumption_l * 1.63, rel=1e-12)
        assert r.practical_consumption_kg == pytest.approx(r.practical_consumption_l * 1.63, rel=1e-12)

    def test_area_scaling_preserves_per_m2_result(self):
        r = calculate_layer(
            LayerCalcInput(
                density=1.45,
                solids_by_volume_percent=72.0,
                dry_thickness=180.0,
                losses_percent=5.0,
            )
        )
        area = 1234.567
        assert scale_to_area(r.practical_consumption_l, area) / area == pytest.approx(r.practical_consumption_l, rel=1e-12)
        assert scale_to_area(r.practical_consumption_kg, area) / area == pytest.approx(r.practical_consumption_kg, rel=1e-12)

    @pytest.mark.parametrize(
        "basis,expected_factor",
        [
            (DILUTION_BASIS_BY_PAINT_VOLUME, 1.125),
            (DILUTION_BASIS_BY_MIX_VOLUME, 1.0 / (1.0 - 0.125)),
            (DILUTION_BASIS_BY_MASS, 1.5 * 0.125 / 0.75 + 1.0),
            (DILUTION_BASIS_BY_COMPONENT_VOLUME, 1.125),
        ],
    )
    def test_dilution_basis_unit_consistency(self, basis, expected_factor):
        dft = 100.0
        base = calculate_wft(dft, 80.0)
        wft = calculate_layer(
            LayerCalcInput(
                density=1.5,
                solids_by_volume_percent=80.0,
                dry_thickness=dft,
                thinner_percent=12.5,
                thinner_density=0.75,
                thinner_basis=basis,
            )
        ).wft
        assert wft == pytest.approx(base * expected_factor)


class TestExcelConsistency:
    def test_primer_excel_row7(self):
        r = calculate_layer(
            LayerCalcInput(density=1.4, solids_by_volume_percent=73, dry_thickness=200, price_per_kg=552)
        )
        assert r.wft == pytest.approx(200 * 100 / 73)
        assert r.theoretical_coverage == pytest.approx(10 * 73 / 200)
        assert r.theoretical_consumption_l == pytest.approx(200 / 10 / 73)
        assert r.theoretical_consumption_kg == pytest.approx(200 / 10 / 73 * 1.4)

    def test_finish_excel_row8(self):
        r = calculate_layer(
            LayerCalcInput(density=1.3, solids_by_volume_percent=58, dry_thickness=100, price_per_kg=892)
        )
        assert r.wft == pytest.approx(100 * 100 / 58)
        assert r.theoretical_coverage == pytest.approx(10 * 58 / 100)
        assert r.theoretical_consumption_l == pytest.approx(100 / 10 / 58)
        assert r.theoretical_consumption_kg == pytest.approx(100 / 10 / 58 * 1.3)
