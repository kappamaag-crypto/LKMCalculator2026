"""Regression tests for §22: unknown engineering inputs must stay unknown."""
from __future__ import annotations

import inspect

import pytest

from app.domain.formulas import (
    DILUTION_BASIS_BY_COMPONENT_VOLUME,
    DILUTION_BASIS_BY_MASS,
    DILUTION_BASIS_BY_MIX_VOLUME,
    DILUTION_BASIS_BY_PAINT_VOLUME,
    calculate_thinner,
    calculate_wft_with_dilution,
)
from app.domain.models import Material


@pytest.mark.parametrize(
    "function,parameter",
    [
        (calculate_wft_with_dilution, "thinner_density"),
        (calculate_wft_with_dilution, "paint_density"),
        (calculate_thinner, "thinner_density"),
        (calculate_thinner, "parent_density"),
        (calculate_thinner, "basis"),
    ],
)
def test_engineering_required_dilution_parameters_have_no_hidden_defaults(function, parameter):
    default = inspect.signature(function).parameters[parameter].default
    assert default is inspect.Parameter.empty


def test_material_unknown_thinner_basis_is_none():
    assert Material().thinner_basis is None


def test_zero_dilution_remains_valid_without_thinner_engineering_data():
    result = calculate_wft_with_dilution(100.0, 70.0, 0.0, None, None, None)
    assert result == pytest.approx(100.0 / 0.70)


def test_unknown_thinner_density_is_not_coerced_to_one():
    with pytest.raises(ValueError, match="плотност.*разбавител"):
        calculate_wft_with_dilution(
            100.0,
            70.0,
            10.0,
            None,
            1.4,
            DILUTION_BASIS_BY_PAINT_VOLUME,
        )


@pytest.mark.parametrize(
    "basis,expected_l",
    [
        (DILUTION_BASIS_BY_PAINT_VOLUME, 0.10),
        (DILUTION_BASIS_BY_MIX_VOLUME, 0.10 / 0.90),
        (DILUTION_BASIS_BY_MASS, 1.0 * 1.4 * 0.10 / 0.8),
        (DILUTION_BASIS_BY_COMPONENT_VOLUME, 0.10),
    ],
)
def test_all_four_dilution_bases_are_explicit_and_calculated(basis, expected_l):
    thinner_l, thinner_kg, _ = calculate_thinner(
        1.0,
        10.0,
        0.8,
        None,
        basis,
        1.4,
    )
    assert thinner_l == pytest.approx(expected_l)
    assert thinner_kg == pytest.approx(expected_l * 0.8)


def test_unknown_basis_is_not_coerced_to_paint_volume():
    with pytest.raises(ValueError, match="основание дозирования"):
        calculate_thinner(1.0, 10.0, 0.8, None, None, 1.4)


def test_mass_basis_without_parent_density_is_unknown_not_one():
    with pytest.raises(ValueError, match="Плотность ЛКМ"):
        calculate_thinner(1.0, 10.0, 0.8, None, DILUTION_BASIS_BY_MASS, None)
