"""Тесты calculation engine."""

from __future__ import annotations

import pytest

from app.domain.models import Material, ObjectData, CoatingSystem, LayerDefinition
from app.domain.enums import MaterialType, BinderType
from app.domain.calculator import LayerCalculator, SystemCalculator, LayerInput
from app.domain.formulas import round3
from app.domain.validation import validate_layer_input, validate_object_data, validate_before_calculation


def make_primer() -> Material:
    return Material(
        id=1,
        manufacturer="Blank",
        brand="Blank",
        material_name="Грунт-Эмаль Blank Universal",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_percent=73.0,
        price_per_kg=552.0,
        recommended_dft_min=100,
        recommended_dft_max=200,
        packaging_kg=20.0,
    )


def make_finish() -> Material:
    return Material(
        id=2,
        manufacturer="Blank",
        brand="Blank",
        material_name="Эмаль Blank Finish",
        material_type=MaterialType.FINISH,
        binder_type=BinderType.POLYURETHANE,
        density=1.3,
        solids_percent=58.0,
        price_per_kg=892.0,
        recommended_dft_min=60,
        recommended_dft_max=100,
        packaging_kg=20.0,
    )


def make_thinner() -> Material:
    return Material(
        id=3,
        material_name="Разбавитель для грунта",
        material_type=MaterialType.THINNER,
        density=0.9,
        solids_percent=0.0,
        price_per_kg=100.0,
    )


class TestLayerCalculator:
    def test_primer_basic(self):
        mat = make_primer()
        result = LayerCalculator.calculate(mat, target_dft=200.0, losses_percent=0.0, area_m2=1.0)

        assert result.wft == round3(200 * 100 / 73)
        assert result.theoretical_coverage == round3(10 * 73 / 200)
        assert result.practical_consumption_kg == round3(200 / 10 / 73 * 1.4)
        assert result.cost_per_m2 == round3(result.practical_consumption_kg * 552.0)

    def test_with_area(self):
        mat = make_primer()
        result = LayerCalculator.calculate(mat, target_dft=200.0, area_m2=100.0)
        assert result.total_consumption_kg == round3(result.practical_consumption_kg * 100)
        assert result.total_cost == round3(result.cost_per_m2 * 100)

    def test_packages(self):
        mat = make_primer()
        result = LayerCalculator.calculate(mat, target_dft=200.0, area_m2=1000.0)
        # required ≈ 0.384 * 1000 = 384 kg, packaging 20 → 20 packages
        assert result.packages_count == 20  # ceil(384/20)=20? 384/20=19.2 → 20
        assert result.purchase_kg >= result.total_consumption_kg

    def test_with_thinner(self):
        mat = make_primer()
        thinner = make_thinner()
        result = LayerCalculator.calculate(
            mat, target_dft=200.0, thinner_percent=5.0, thinner=thinner, area_m2=1.0
        )
        assert result.thinner_consumption_l > 0
        assert result.thinner_consumption_kg > 0
        assert result.thinner_cost_per_m2 > 0


class TestSystemCalculator:
    def test_two_layer_system(self):
        primer = make_primer()
        finish = make_finish()
        obj = ObjectData(object_name="Тест", area_m2=100.0)

        layers = [
            LayerInput(material=primer, target_dft=200.0, losses_percent=0.0),
            LayerInput(material=finish, target_dft=100.0, losses_percent=0.0),
        ]

        calc = SystemCalculator()
        result, validation = calc.calculate(obj, layers)

        assert not validation.has_errors
        assert result.total_dft == 300.0
        assert len(result.layers) == 2
        assert result.total_cost_per_m2 > 0
        assert result.total_cost == round3(result.total_cost_per_m2 * 100)

    def test_area_from_elements(self):
        primer = make_primer()
        obj = ObjectData(area_per_element=50.0, elements_count=4)  # 200 м²
        layers = [LayerInput(material=primer, target_dft=200.0)]
        calc = SystemCalculator()
        result, _ = calc.calculate(obj, layers)
        assert result.layers[0].total_consumption_kg == round3(
            result.layers[0].practical_consumption_kg * 200
        )


class TestValidation:
    def test_negative_area(self):
        obj = ObjectData(area_m2=-10)
        r = validate_object_data(obj)
        assert r.has_errors
        assert any(i.code == "OBJ_AREA_NEG" for i in r.errors)

    def test_dft_above_max(self):
        mat = make_primer()
        r = validate_layer_input(mat, target_dft=250.0)
        assert r.has_warnings
        assert any(i.code == "LAYER_DFT_ABOVE_MAX" for i in r.warnings)

    def test_solids_over_100(self):
        mat = make_primer()
        mat.solids_percent = 120.0
        r = validate_layer_input(mat, target_dft=100.0)
        assert r.has_errors
        assert any(i.code == "MAT_SOLIDS_GT100" for i in r.errors)

    def test_losses_ge_100(self):
        mat = make_primer()
        r = validate_layer_input(mat, target_dft=100.0, losses_percent=100.0)
        assert r.has_errors

    def test_dew_point(self):
        obj = ObjectData(area_m2=10, surface_temperature=5.0, dew_point=8.0)
        r = validate_object_data(obj)
        assert r.has_errors
        assert any(i.code == "OBJ_DEW_POINT" for i in r.errors)

    def test_before_calculation_blocks_on_error(self):
        mat = make_primer()
        mat.density = -1.0
        obj = ObjectData(area_m2=10)
        r = validate_before_calculation(obj, [(mat, 200.0, 0.0, 0.0)])
        assert r.has_errors


class TestComparison:
    def test_compare_two_systems(self):
        from app.domain.comparison import ComparisonEngine

        primer = make_primer()
        finish = make_finish()
        obj = ObjectData(area_m2=100.0)

        sys1 = [
            LayerInput(material=primer, target_dft=200.0),
            LayerInput(material=finish, target_dft=100.0),
        ]
        sys2 = [
            LayerInput(material=primer, target_dft=150.0),
            LayerInput(material=finish, target_dft=80.0),
        ]

        engine = ComparisonEngine()
        comparison = engine.compare(obj, [("Система А", sys1), ("Система Б", sys2)])

        assert len(comparison.systems) == 2
        assert comparison.cheapest_index is not None
        assert comparison.thinnest_index is not None
        assert comparison.best_balance_index is not None

        table = engine.to_table(comparison)
        assert len(table) >= 5
        assert table[0]["indicator"] == "Название"