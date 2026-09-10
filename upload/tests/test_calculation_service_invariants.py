"""Регрессионные инварианты SystemCalculationResult / CalculationService."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData
from app.services.calculation_service import CalculationService


def _material(name: str, density: float, solids: float, price: float) -> Material:
    return Material(
        material_name=name,
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=density,
        solids_percent=solids,
        solids_by_volume_percent=solids,
        price_per_kg=price,
    )


def _layers(count: int) -> list[LayerInput]:
    return [
        LayerInput(
            material=_material(
                f"Материал {i}",
                density=1.27 + i * 0.083,
                solids=61.3 + i * 4.7,
                price=417.25 + i * 93.15,
            ),
            target_dft=83.5 + i * 37.25,
            losses_percent=3.75 + i * 1.125,
        )
        for i in range(1, count + 1)
    ]


@pytest.mark.parametrize("layer_count", [2, 3, 4, 5])
def test_system_totals_are_exact_sums_of_layer_results(layer_count: int):
    obj = ObjectData(object_name="Golden", area_m2=137.35)
    result, validation = CalculationService().calculate_system(obj, _layers(layer_count))

    assert not validation.has_errors
    assert len(result.layers) == layer_count
    assert result.total_dft == pytest.approx(sum(x.target_dft for x in result.layers), rel=0, abs=1e-12)
    assert result.total_theoretical_consumption_kg == pytest.approx(
        sum(x.theoretical_consumption_kg for x in result.layers), rel=0, abs=1e-15
    )
    assert result.total_practical_consumption_kg == pytest.approx(
        sum(x.practical_consumption_kg for x in result.layers), rel=0, abs=1e-15
    )
    assert result.total_theoretical_consumption_l == pytest.approx(
        sum(x.theoretical_consumption_l for x in result.layers), rel=0, abs=1e-15
    )
    assert result.total_practical_consumption_l == pytest.approx(
        sum(x.practical_consumption_l for x in result.layers), rel=0, abs=1e-15
    )
    assert result.total_cost_per_m2 == pytest.approx(
        sum(x.cost_per_m2 + x.thinner_cost_per_m2 for x in result.layers), rel=0, abs=1e-12
    )
    assert result.total_thinner_cost == pytest.approx(
        sum(x.thinner_cost_per_m2 * obj.area_m2 for x in result.layers), rel=0, abs=1e-12
    )
    assert result.total_cost == pytest.approx(
        sum(x.total_cost for x in result.layers), rel=0, abs=1e-10
    )


def test_system_area_scaling_is_linear_and_per_m2_is_area_independent():
    service = CalculationService()
    layers = _layers(4)
    small, validation_small = service.calculate_system(
        ObjectData(object_name="Small", area_m2=1.0), layers
    )
    large, validation_large = service.calculate_system(
        ObjectData(object_name="Large", area_m2=913.75), layers
    )

    assert not validation_small.has_errors
    assert not validation_large.has_errors
    assert large.total_practical_consumption_kg == pytest.approx(
        small.total_practical_consumption_kg, rel=0, abs=1e-15
    )
    assert large.total_practical_consumption_l == pytest.approx(
        small.total_practical_consumption_l, rel=0, abs=1e-15
    )
    assert large.total_cost_per_m2 == pytest.approx(
        small.total_cost_per_m2, rel=0, abs=1e-12
    )
    assert large.total_cost == pytest.approx(
        small.total_cost * 913.75, rel=1e-12, abs=1e-9
    )
    assert large.total_thinner_cost == pytest.approx(
        small.total_thinner_cost * 913.75, rel=1e-12, abs=1e-9
    )


def test_system_totals_keep_full_precision_without_intermediate_rounding():
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="Precision", area_m2=37.125),
        [
            LayerInput(
                material=_material("Точный материал", 1.3765, 67.35, 583.275),
                target_dft=137.55,
                losses_percent=7.375,
            ),
            LayerInput(
                material=_material("Второй точный материал", 1.4895, 72.85, 721.625),
                target_dft=93.275,
                losses_percent=4.625,
            ),
            LayerInput(
                material=_material("Третий точный материал", 1.6125, 59.45, 814.875),
                target_dft=51.825,
                losses_percent=9.125,
            ),
        ],
    )

    assert not validation.has_errors
    assert result.total_dft == pytest.approx(282.65, rel=0, abs=1e-12)
    raw_sum = sum(layer.practical_consumption_kg for layer in result.layers)
    assert result.total_practical_consumption_kg == pytest.approx(raw_sum, rel=0, abs=1e-15)
    assert result.total_practical_consumption_kg != pytest.approx(
        round(raw_sum, 3), rel=0, abs=1e-15
    )
