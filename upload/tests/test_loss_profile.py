"""Tests for LossProfile and resolve_losses priority."""
from __future__ import annotations

import pytest

from app.domain.calculator import LayerCalculator, SystemCalculator
from app.domain.enums import BinderType, MaterialType
from app.domain.models import LossProfile, Material


def make_primer(**kwargs) -> Material:
    defaults = dict(
        material_name="Test primer",
        material_type=MaterialType.PRIMER,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=70.0,
        price_per_kg=500.0,
    )
    defaults.update(kwargs)
    return Material(**defaults)


class TestLossProfileIntegration:
    def test_explicit_losses_win(self):
        profile = LossProfile(name="p", percent=30)
        calc = SystemCalculator(default_losses=5.0, loss_profile=profile)
        r = LayerCalculator.calculate(make_primer(), 100, losses_percent=10)
        assert r.losses_percent == 10

    def test_profile_used_when_explicit_none(self):
        profile = LossProfile(name="p", percent=25)
        # SystemCalculator path exercises resolve_losses
        calc = SystemCalculator(default_losses=5.0, loss_profile=profile)
        resolved = calc.resolve_losses(explicit_percent=None)
        assert resolved.percent == 25.0
        assert resolved.source == "PROFILE"

    def test_default_when_no_profile(self):
        calc = SystemCalculator(default_losses=12.0)
        resolved = calc.resolve_losses(explicit_percent=None)
        assert resolved.percent == 12.0
        assert resolved.source == "DEFAULT"

    def test_invalid_losses_validation(self):
        from app.domain.calculator import LayerInput
        from app.domain.models import ObjectData

        calc = SystemCalculator()
        result, validation = calc.calculate_system(
            ObjectData(area_m2=10.0),
            [LayerInput(material=make_primer(), target_dft=100, losses_percent=100)],
        )
        assert validation.has_errors
        assert any(i.code == "LAYER_LOSSES_INVALID" for i in validation.errors)
        assert result.layers == []

    def test_existing_layer_calculator_api_unchanged(self):
        r = LayerCalculator.calculate(make_primer(), 200, losses_percent=10)
        assert r.losses_percent == 10
        assert r.practical_consumption_kg > 0

    def test_resolve_losses_helper_priority(self):
        profile = LossProfile(name="p", percent=30)
        calc = SystemCalculator(default_losses=5.0, loss_profile=profile)
        r = calc.resolve_losses(explicit_percent=7.0)
        assert r.percent == 7.0 and r.source == "EXPLICIT"
        r = calc.resolve_losses(explicit_percent=None)
        assert r.percent == 30.0 and r.source == "PROFILE"
        calc2 = SystemCalculator(default_losses=5.0)
        r = calc2.resolve_losses(explicit_percent=None)
        assert r.percent == 5.0 and r.source == "DEFAULT"
