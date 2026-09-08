"""Тесты calculation engine."""

from __future__ import annotations

import pytest

from app.domain.models import Material, ObjectData, CoatingSystem, LayerDefinition
from app.domain.enums import MaterialType, BinderType
from app.domain.calculator import LayerCalculator, SystemCalculator, LayerInput
from app.domain.formulas import round3


def make_primer() -> Material:
    return Material(
        id=1, manufacturer="Blank", brand="Blank",
        material_name="\u0413\u0440\u0443\u043d\u0442-\u042d\u043c\u0430\u043b\u044c Blank Universal",
        material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY,
        density=1.4, solids_percent=73.0, price_per_kg=552.0,
        recommended_dft_min=100, recommended_dft_max=200, packaging_kg=20.0,
    )


def make_finish() -> Material:
    return Material(
        id=2, manufacturer="Blank", brand="Blank",
        material_name="\u042d\u043c\u0430\u043b\u044c Blank Finish",
        material_type=MaterialType.FINISH, binder_type=BinderType.POLYURETHANE,
        density=1.3, solids_percent=58.0, price_per_kg=892.0,
        recommended_dft_min=60, recommended_dft_max=100, packaging_kg=20.0,
    )


def make_thinner() -> Material:
    return Material(
        id=3, material_name="\u0420\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c",
        material_type=MaterialType.THINNER, density=0.9, solids_percent=0.0, price_per_kg=100.0,
    )


class TestLayerCalculator:
    def test_primer_basic(self):
        result = LayerCalculator.calculate(make_primer(), target_dft=200.0, losses_percent=0.0, area_m2=1.0)
        assert result.wft == round3(200 * 100 / 73)
        assert result.theoretical_coverage == round3(10 * 73 / 200)
        assert result.practical_consumption_kg == round3(200 / 10 / 73 * 1.4)
        assert result.cost_per_m2 == round3(result.practical_consumption_kg * 552.0)

    def test_with_area(self):
        result = LayerCalculator.calculate(make_primer(), target_dft=200.0, area_m2=100.0)
        assert result.total_consumption_kg == round3(result.practical_consumption_kg * 100)
        assert result.total_cost == round3(result.cost_per_m2 * 100)

    def test_packages(self):
        result = LayerCalculator.calculate(make_primer(), target_dft=200.0, area_m2=1000.0)
        assert result.packages_count >= 1
        assert result.purchase_kg >= result.total_consumption_kg

    def test_thinner(self):
        result = LayerCalculator.calculate(
            make_primer(), target_dft=200.0, thinner_percent=5.0,
            thinner=make_thinner(), area_m2=1.0,
        )
        assert result.thinner_consumption_l > 0
        assert result.thinner_cost_per_m2 > 0


class TestSystemCalculator:
    def test_two_layers(self):
        obj = ObjectData(object_name="Test", area_m2=100.0)
        layers = [
            LayerInput(material=make_primer(), target_dft=200),
            LayerInput(material=make_finish(), target_dft=100),
        ]
        result, val = SystemCalculator().calculate(obj, layers, skip_validation=True)
        assert len(result.layers) == 2
        assert result.total_dft == 300.0
        assert result.total_cost_per_m2 > 0
        assert result.total_cost == round3(result.total_cost_per_m2 * 100)
