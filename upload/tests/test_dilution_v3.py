"""Регрессионные тесты для расчёта разбавления v3."""

import pytest

from app.domain.formulas import (
    LayerCalcInput,
    calculate_layer,
    calculate_wft_with_dilution,
    DILUTION_BASIS_BY_PAINT_VOLUME,
    DILUTION_BASIS_BY_MIX_VOLUME,
    DILUTION_BASIS_BY_MASS,
)


def test_dilution_by_paint_volume_changes_wft_but_not_paint_consumption():
    result = calculate_layer(LayerCalcInput(density=1.4, solids_by_volume_percent=70.0, dry_thickness=100.0,
        thinner_percent=20.0, thinner_density=0.9, thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME))
    assert result.wft == pytest.approx((100.0 / 0.70) * 1.20)
    assert result.theoretical_consumption_l == pytest.approx(100.0 / 0.70 / 1000.0)
    assert result.thinner_consumption_l == pytest.approx(result.practical_consumption_l * 0.20)


def test_dilution_by_mix_volume():
    wft = calculate_wft_with_dilution(100.0, 70.0, 20.0, 0.9, 1.4, DILUTION_BASIS_BY_MIX_VOLUME)
    assert wft == pytest.approx((100.0 / 0.70) / 0.80)


def test_dilution_by_mass_uses_both_densities_without_intermediate_rounding():
    wft = calculate_wft_with_dilution(100.0, 70.0, 20.0, paint_density=1.4,
        thinner_density=0.9, basis=DILUTION_BASIS_BY_MASS)
    expected = (100.0 / 0.70) * (1.0 + (1.4 * 0.20 / 0.9))
    assert wft == pytest.approx(expected)


@pytest.mark.parametrize("percent", [-0.01, 100.0, 100.01])
def test_invalid_dilution_percent_is_rejected(percent):
    with pytest.raises(ValueError):
        calculate_wft_with_dilution(100.0, 70.0, percent, 0.9, 1.4, DILUTION_BASIS_BY_PAINT_VOLUME)


def test_invalid_dilution_percent_is_rejected_even_when_dft_zero():
    with pytest.raises(ValueError):
        calculate_wft_with_dilution(0.0, 70.0, 100.0, 0.9, 1.4, DILUTION_BASIS_BY_PAINT_VOLUME)
