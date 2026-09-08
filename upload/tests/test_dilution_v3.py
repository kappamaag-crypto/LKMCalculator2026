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
    result = calculate_layer(
        LayerCalcInput(
            density=1.4,
            solids_percent=70.0,
            dry_thickness=100.0,
            thinner_percent=20.0,
            thinner_density=0.9,
            thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME,
        )
    )

    # Без разбавления WFT = 100 / 0.70 = 142.857 мкм.
    assert result.wft == pytest.approx(171.429, abs=0.001)
    # Для 20% от объёма исходного ЛКМ расход самого ЛКМ определяется
    # сухим остатком и не должен искусственно вырасти в 1.2 раза.
    assert result.theoretical_consumption_l == pytest.approx(0.143, abs=0.001)
    assert result.thinner_consumption_l == pytest.approx(0.029, abs=0.001)


def test_dilution_by_mix_volume():
    wft = calculate_wft_with_dilution(
        dft=100.0,
        solids_percent=70.0,
        thinner_percent=20.0,
        basis=DILUTION_BASIS_BY_MIX_VOLUME,
    )
    # 20% от конечного объёма => объём смеси увеличивается в 1/(1-0.2)=1.25 раза.
    assert wft == pytest.approx(178.571, abs=0.001)


def test_dilution_by_mass_uses_both_densities():
    wft = calculate_wft_with_dilution(
        dft=100.0,
        solids_percent=70.0,
        thinner_percent=20.0,
        paint_density=1.4,
        thinner_density=0.9,
        basis=DILUTION_BASIS_BY_MASS,
    )
    expected = (100.0 / 0.70) * (1.0 + (1.4 * 0.20 / 0.9))
    assert wft == pytest.approx(round(expected, 3), abs=0.001)


def test_invalid_dilution_percent_is_rejected():
    with pytest.raises(ValueError):
        calculate_wft_with_dilution(
            dft=100,
            solids_percent=70,
            thinner_percent=100,
            basis=DILUTION_BASIS_BY_PAINT_VOLUME,
        )
