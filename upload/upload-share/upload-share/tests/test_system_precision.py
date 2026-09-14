"""System-level precision and unit invariants for АКЗ v3.0."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService


def _material(index: int) -> Material:
    return Material(
        manufacturer="Golden",
        material_name=f"Golden layer {index}",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.31 + index * 0.07,
        solids_by_volume_percent=61.7 + index * 2.3,
        price_per_kg=417.0 + index * 83.0,
    )


@pytest.mark.parametrize("layer_count", [2, 3, 4, 5])
def test_system_totals_match_independent_multilayer_golden_calculation(layer_count):
    area = 137.35
    inputs = [
        LayerInput(
            material=_material(i),
            target_dft=83.5 + i * 27.25,
            losses_percent=3.75 + i * 1.15,
        )
        for i in range(1, layer_count + 1)
    ]
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name=f"Golden {layer_count}", area_m2=area), inputs
    )
    assert not validation.has_errors

    expected_dft = sum(layer.target_dft for layer in inputs)
    expected_l = 0.0
    expected_kg = 0.0
    expected_cost = 0.0
    for layer in inputs:
        base_l = (layer.target_dft * 100.0 / layer.material.solids_by_volume_percent) / 1000.0
        practical_l = base_l * 100.0 / (100.0 - layer.losses_percent)
        practical_kg = practical_l * layer.material.density
        expected_l += practical_l
        expected_kg += practical_kg
        expected_cost += practical_kg * layer.material.price_per_kg

    assert result.total_dft == pytest.approx(expected_dft, rel=1e-13, abs=1e-14)
    assert result.total_theoretical_consumption_l == pytest.approx(
        sum((l.target_dft * 100.0 / l.material.solids_by_volume_percent) / 1000.0 for l in inputs),
        rel=1e-13,
        abs=1e-14,
    )
    assert result.total_practical_consumption_l == pytest.approx(expected_l, rel=1e-13, abs=1e-14)
    assert result.total_practical_consumption_kg == pytest.approx(expected_kg, rel=1e-13, abs=1e-14)
    assert result.total_cost_per_m2 == pytest.approx(expected_cost, rel=1e-13, abs=1e-12)
    assert result.total_cost == pytest.approx(expected_cost * area, rel=1e-13, abs=1e-10)


def test_system_area_scaling_changes_only_object_totals():
    material = _material(3)
    layers = [LayerInput(material=material, target_dft=137.5, losses_percent=7.25)]
    service = CalculationService()
    small, validation_small = service.calculate_system(
        ObjectData(object_name="A", area_m2=1.0), layers
    )
    large, validation_large = service.calculate_system(
        ObjectData(object_name="B", area_m2=913.75), layers
    )
    assert not validation_small.has_errors
    assert not validation_large.has_errors
    assert large.total_practical_consumption_l == pytest.approx(small.total_practical_consumption_l)
    assert large.total_practical_consumption_kg == pytest.approx(small.total_practical_consumption_kg)
    assert large.total_cost_per_m2 == pytest.approx(small.total_cost_per_m2)
    assert large.layers[0].total_consumption_l == pytest.approx(small.layers[0].total_consumption_l * 913.75)
    assert large.layers[0].total_consumption_kg == pytest.approx(small.layers[0].total_consumption_kg * 913.75)
    assert large.total_cost == pytest.approx(small.total_cost * 913.75)


def test_system_keeps_full_precision_until_result_boundary():
    material = _material(4)
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="Precision", area_m2=333.333),
        [
            LayerInput(material=material, target_dft=111.125, losses_percent=6.375),
            LayerInput(material=_material(5), target_dft=97.875, losses_percent=8.625),
        ],
    )
    assert not validation.has_errors
    layer_sum = sum(layer.practical_consumption_l for layer in result.layers)
    assert result.total_practical_consumption_l == pytest.approx(layer_sum, rel=1e-15, abs=1e-15)
    assert result.total_practical_consumption_l != pytest.approx(
        round(result.total_practical_consumption_l, 3), rel=0, abs=1e-15
    )
