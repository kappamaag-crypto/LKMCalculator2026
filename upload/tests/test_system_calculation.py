"""Интеграционные тесты расчёта многослойной системы АКЗ."""

from __future__ import annotations

import pytest

from app.domain.calculator import LayerInput, SystemCalculator
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME
from app.domain.models import CoatingSystem, Material, ObjectData


def material(name: str, density: float, solids: float, price: float) -> Material:
    return Material(
        manufacturer="TEST",
        material_name=name,
        density=density,
        solids_by_volume_percent=solids,
        price_per_kg=price,
    )


def test_three_layer_system_totals_and_costs() -> None:
    primer = material("Primer", 1.40, 70.0, 500.0)
    intermediate = material("Intermediate", 1.50, 65.0, 600.0)
    finish = material("Finish", 1.30, 58.0, 800.0)
    thinner = material("Thinner", 0.80, 100.0, 100.0)

    obj = ObjectData(area_m2=1000.0)
    system = CoatingSystem(system_name="TEST-3L")
    inputs = [
        LayerInput(primer, 80.0, losses_percent=10.0, thinner_percent=5.0, thinner=thinner, thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME),
        LayerInput(intermediate, 120.0, losses_percent=20.0),
        LayerInput(finish, 60.0, losses_percent=15.0, thinner_percent=8.0, thinner=thinner, thinner_basis=DILUTION_BASIS_BY_PAINT_VOLUME),
    ]

    result, validation = SystemCalculator().calculate(
        obj, inputs, system=system, skip_validation=True
    )

    assert not validation.has_errors
    assert len(result.layers) == 3
    assert result.total_dft == pytest.approx(260.0)
    assert result.total_practical_consumption_kg == pytest.approx(
        sum(layer.practical_consumption_kg for layer in result.layers)
    )
    assert result.total_practical_consumption_l == pytest.approx(
        sum(layer.practical_consumption_l for layer in result.layers)
    )
    assert result.total_cost_per_m2 == pytest.approx(
        sum(layer.cost_per_m2 + layer.thinner_cost_per_m2 for layer in result.layers)
    )
    assert result.total_cost == pytest.approx(result.total_cost_per_m2 * 1000.0)
    assert result.total_thinner_cost == pytest.approx(
        sum(layer.thinner_cost_per_m2 * 1000.0 for layer in result.layers)
    )

    assert result.total_thinner_cost > 0
    assert result.total_cost > result.total_thinner_cost

    # В расчётном результате нет закупочной/складской логики.
    assert not hasattr(result, "procurement_quantity")
    assert not hasattr(result, "package_count")
    assert not hasattr(result, "leftover")
    assert not hasattr(result, "warehouse_balance")


def test_direct_area_is_the_only_object_area_input() -> None:
    primer = material("Primer", 1.40, 70.0, 500.0)
    obj = ObjectData(area_m2=1000.0)

    result, validation = SystemCalculator().calculate(
        obj,
        [LayerInput(primer, 100.0)],
        skip_validation=True,
    )

    assert not validation.has_errors
    assert result.total_cost == pytest.approx(result.total_cost_per_m2 * 1000.0)
    assert result.layers[0].total_consumption_kg == pytest.approx(
        result.layers[0].practical_consumption_kg * 1000.0
    )


def test_losses_are_applied_per_layer() -> None:
    material_a = material("A", 1.40, 70.0, 500.0)
    material_b = material("B", 1.40, 70.0, 500.0)
    obj = ObjectData(area_m2=100.0)

    result, _ = SystemCalculator().calculate(
        obj,
        [
            LayerInput(material_a, 100.0, losses_percent=0.0),
            LayerInput(material_b, 100.0, losses_percent=25.0),
        ],
        skip_validation=True,
    )

    assert result.layers[0].losses_percent == pytest.approx(0.0)
    assert result.layers[1].losses_percent == pytest.approx(25.0)
    assert result.layers[1].practical_consumption_kg > result.layers[0].practical_consumption_kg
