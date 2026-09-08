"""Unit-тесты расчётных формул (1:1 со старым калькулятором)."""

from __future__ import annotations

import pytest

from app.domain.formulas import (
    calculate_wft,
    calculate_theoretical_coverage,
    calculate_loss_coefficient,
    calculate_practical_coverage,
    calculate_consumption_l,
    calculate_consumption_kg,
    calculate_cost,
    calculate_thinner,
    calculate_layer,
    LayerCalcInput,
    scale_to_area,
    calculate_packages,
    total_area,
    round3,
)


class TestBasicFormulas:
    def test_wft_primer(self):
        wft = calculate_wft(200.0, 73.0)
        assert wft == round3(200 * 100 / 73)

    def test_wft_finish(self):
        wft = calculate_wft(100.0, 58.0)
        assert wft == round3(100 * 100 / 58)

    def test_wft_zero_inputs(self):
        assert calculate_wft(0, 73) == 0.0
        assert calculate_wft(200, 0) == 0.0

    def test_theoretical_coverage(self):
        wft = calculate_wft(200.0, 73.0)
        cov = calculate_theoretical_coverage(wft)
        assert cov == round3(1000.0 / wft)

    def test_loss_coefficient(self):
        assert calculate_loss_coefficient(0) == 1.0
        assert calculate_loss_coefficient(20) == pytest.approx(100 / 80)
        assert calculate_loss_coefficient(100) == 1.0
        assert calculate_loss_coefficient(-5) == 1.0

    def test_practical_coverage(self):
        pract = calculate_practical_coverage(10.0, 1.25)
        assert pract == round3(10.0 / 1.25)

    def test_consumption_and_cost(self):
        inp = LayerCalcInput(
            density=1.4, solids_percent=73.0, dry_thickness=200.0,
            losses_percent=0.0, price_per_kg=552.0,
        )
        result = calculate_layer(inp)
        assert result.wft == round3(200 * 100 / 73)
        assert result.theoretical_coverage == round3(1000 / result.wft)
        assert result.practical_coverage == result.theoretical_coverage
        assert result.theoretical_consumption_kg == round3(result.theoretical_consumption_l * 1.4)
        assert result.cost_per_m2 == round3(result.practical_consumption_kg * 552.0)

    def test_with_losses(self):
        inp = LayerCalcInput(
            density=1.4, solids_percent=73.0, dry_thickness=200.0,
            losses_percent=20.0, price_per_kg=552.0,
        )
        result = calculate_layer(inp)
        k = 100 / 80
        assert result.loss_coefficient == pytest.approx(k)
        assert result.practical_coverage == round3(result.theoretical_coverage / k)
        assert result.practical_consumption_kg > result.theoretical_consumption_kg

    def test_thinner(self):
        thinner_l, thinner_kg, cost = calculate_thinner(
            parent_consumption_l=0.274, thinner_percent=5.0,
            thinner_density=0.9, thinner_price_per_kg=100.0,
        )
        expected_l = round3(0.274 * 0.05)
        expected_kg = round3(expected_l * 0.9)
        assert thinner_l == expected_l
        assert thinner_kg == expected_kg
        assert cost == round3(expected_kg * 100.0)

    def test_scale_to_area(self):
        assert scale_to_area(0.5, 100) == 50.0
        assert scale_to_area(0.5, 0) == 0.0

    def test_packages(self):
        packages, purchase, remainder = calculate_packages(1235.0, 20.0)
        assert packages == 62
        assert purchase == 1240.0
        assert remainder == 5.0

    def test_total_area(self):
        assert total_area(1250.0, 5) == 6250.0
        assert total_area(0, 5) == 0.0


class TestExcelConsistency:
    def test_primer_excel_row7(self):
        inp = LayerCalcInput(
            density=1.4, solids_percent=73.0, dry_thickness=200.0,
            losses_percent=0.0, price_per_kg=552.0,
        )
        r = calculate_layer(inp)
        assert r.wft == round3(200 * 100 / 73)
        excel_covering = round3(10 * 73 / 200)
        assert r.theoretical_coverage == excel_covering
        excel_kg = round3(200 / 10 / 73 * 1.4)
        assert r.theoretical_consumption_kg == excel_kg

    def test_finish_excel_row8(self):
        inp = LayerCalcInput(
            density=1.3, solids_percent=58.0, dry_thickness=100.0,
            losses_percent=0.0, price_per_kg=892.0,
        )
        r = calculate_layer(inp)
        assert r.wft == round3(100 * 100 / 58)
        excel_covering = round3(10 * 58 / 100)
        assert r.theoretical_coverage == excel_covering
        excel_kg = round3(100 / 10 / 58 * 1.3)
        assert r.theoretical_consumption_kg == excel_kg
