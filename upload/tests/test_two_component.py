from decimal import Decimal

import pytest

from app.domain.two_component import (
    MaterialComponent,
    MaterialMix,
    TwoComponentCalculationError,
    TwoComponentService,
)


def test_two_component_mass_ratio_4_to_1():
    result = TwoComponentService.calculate(
        required_mix_kg=20.0,
        mix=MaterialMix(material_id=1, mix_ratio_a=4.0, mix_ratio_b=1.0, ratio_basis="mass"),
        component_a=MaterialComponent(component_code="A", packaging_kg=16.0, price_per_kg=100.0),
        component_b=MaterialComponent(component_code="B", packaging_kg=4.0, price_per_kg=200.0),
    )
    assert result.component_a_kg == pytest.approx(16.0)
    assert result.component_b_kg == pytest.approx(4.0)
    assert result.sets == 1
    assert result.purchase_a_kg == pytest.approx(16.0)
    assert result.purchase_b_kg == pytest.approx(4.0)
    assert result.total_cost == Decimal("2400.00")


def test_two_component_requires_both_package_sizes():
    with pytest.raises(TwoComponentCalculationError):
        TwoComponentService.calculate(
            required_mix_kg=20.0,
            mix=MaterialMix(material_id=1, mix_ratio_a=4.0, mix_ratio_b=1.0),
            component_a=MaterialComponent(component_code="A", packaging_kg=16.0),
            component_b=MaterialComponent(component_code="B"),
        )


def test_two_component_unknown_price_is_not_zero():
    result = TwoComponentService.calculate(
        required_mix_kg=20.0,
        mix=MaterialMix(material_id=1, mix_ratio_a=4.0, mix_ratio_b=1.0),
        component_a=MaterialComponent(component_code="A", packaging_kg=16.0, price_per_kg=100.0),
        component_b=MaterialComponent(component_code="B", packaging_kg=4.0),
    )
    assert result.cost_a == Decimal("1600.00")
    assert result.cost_b is None
    assert result.total_cost is None
