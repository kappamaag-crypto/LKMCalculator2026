"""Regression tests for hard failures on unknown critical calculator inputs."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerCalculator, LayerInput, SystemCalculator
from app.domain.models import Material, ObjectData
from app.domain.enums import MaterialType


def make_material() -> Material:
    return Material(
        material_name="Test coating",
        material_type=MaterialType.PRIMER_ENAMEL,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=500.0,
    )


def test_layer_calculator_rejects_unknown_dft():
    with pytest.raises(ValueError, match="DFT"):
        LayerCalculator.calculate(make_material(), None)


def test_layer_calculator_rejects_zero_area():
    with pytest.raises(ValueError, match="Площадь"):
        LayerCalculator.calculate(make_material(), 100, area_m2=0)


def test_layer_calculator_rejects_unknown_area():
    with pytest.raises(ValueError, match="Площадь"):
        LayerCalculator.calculate(make_material(), 100, area_m2=None)


def test_layer_calculator_rejects_unknown_losses():
    with pytest.raises(ValueError, match="потерь"):
        LayerCalculator.calculate(make_material(), 100, losses_percent=None)


def test_layer_calculator_rejects_unknown_thinner_percent():
    with pytest.raises(ValueError, match="разбавления"):
        LayerCalculator.calculate(make_material(), 100, thinner_percent=None)


def test_system_calculator_unknown_area_returns_validation_error():
    result, validation = SystemCalculator().calculate(
        ObjectData(area_m2=None), [LayerInput(make_material(), 100)]
    )
    assert validation.has_errors
    assert result.layers == []
