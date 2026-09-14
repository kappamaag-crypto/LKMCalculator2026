"""§19 legacy parity: two-component (2K) materials.

v2 has no dedicated 2K domain module. v3 models 2K as informational metadata
(ratio, pot life, components) and calculates the mixed product as **one** material
layer — no purchase/set/remainder inventory math (§8 / domain docstring).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.calculator import LayerInput
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, MaterialComponent, MaterialMix, ObjectData
from app.domain.two_component import (
    RATIO_MASS,
    RATIO_VOLUME,
    TwoComponentCalculationError,
    TwoComponentService,
)
from app.services.calculation_service import CalculationService


def test_v2_has_no_two_component_domain_module():
    root = Path(__file__).resolve().parents[2]
    assert not (root / "v2" / "app" / "domain" / "two_component.py").exists()
    calc = (root / "v2" / "app" / "domain" / "calculator.py").read_text(encoding="utf-8")
    assert "two_component" not in calc
    assert "mix_ratio" not in calc


def test_v3_two_component_describe_is_informational_only():
    result = TwoComponentService.describe(
        mix=MaterialMix(
            material_id=1,
            mix_ratio_a=4.0,
            mix_ratio_b=1.0,
            ratio_basis=RATIO_MASS,
            working_time_minutes=40,
        ),
        component_a=MaterialComponent(component_code="A", name="Base"),
        component_b=MaterialComponent(component_code="B", name="Hardener"),
    )
    assert result.ratio_text == "4:1 по массе"
    assert result.working_time_minutes == 40
    for forbidden in ("purchase_a_kg", "remainder_a_kg", "sets", "kits"):
        assert not hasattr(result, forbidden)


def test_v3_two_component_rejects_invalid_ratio_and_basis():
    with pytest.raises(TwoComponentCalculationError):
        TwoComponentService.describe(
            mix=MaterialMix(material_id=1, mix_ratio_a=0.0, mix_ratio_b=1.0),
            component_a=MaterialComponent(component_code="A"),
            component_b=MaterialComponent(component_code="B"),
        )
    with pytest.raises(TwoComponentCalculationError):
        TwoComponentService.describe(
            mix=MaterialMix(
                material_id=1, mix_ratio_a=2.0, mix_ratio_b=1.0, ratio_basis="unknown"
            ),
            component_a=MaterialComponent(component_code="A"),
            component_b=MaterialComponent(component_code="B"),
        )


def test_v3_two_component_calculates_as_single_mixed_layer():
    two_k = Material(
        manufacturer="Blank",
        material_name="2К Эпоксидный",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.45,
        solids_by_volume_percent=72.0,
        solids_percent=72.0,
        price_per_kg=500.0,
        is_two_component=True,
    )
    finish = Material(
        manufacturer="Blank",
        material_name="Финиш",
        material_type=MaterialType.FINISH,
        binder_type=BinderType.POLYURETHANE,
        density=1.3,
        solids_by_volume_percent=60.0,
        solids_percent=60.0,
        price_per_kg=700.0,
    )
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="2К parity", area_m2=100.0),
        [
            LayerInput(material=two_k, target_dft=120.0, losses_percent=5.0),
            LayerInput(material=finish, target_dft=80.0, losses_percent=5.0),
        ],
    )
    assert not validation.has_errors
    assert len(result.layers) == 2
    assert result.layers[0].material.is_two_component is True
    assert result.layers[0].practical_consumption_kg > 0
    assert all(not hasattr(lr, "component_a_consumption_kg") for lr in result.layers)


def test_v3_volume_ratio_supported():
    result = TwoComponentService.describe(
        mix=MaterialMix(
            material_id=1, mix_ratio_a=2.0, mix_ratio_b=1.0, ratio_basis=RATIO_VOLUME
        ),
        component_a=MaterialComponent(component_code="A"),
        component_b=MaterialComponent(component_code="B"),
    )
    assert result.ratio_text == "2:1 по объёму"
