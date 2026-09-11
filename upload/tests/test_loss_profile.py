"""Regression tests for controlled LossProfile integration (§28)."""

from __future__ import annotations

import pytest

from app.domain.models import Material, ObjectData
from app.domain.enums import MaterialType, BinderType
from app.domain.calculator import LayerCalculator, SystemCalculator, LayerInput
from app.domain.loss_profile import LossProfile
from app.domain.formulas import calculate_loss_coefficient


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
        solids_by_volume_percent=73.0,
        price_per_kg=552.0,
        recommended_dft_min=100,
        recommended_dft_max=200,
        packaging_kg=20.0,
    )


class TestLossProfileModel:
    def test_none_profile_is_zero(self):
        p = LossProfile.none()
        assert p.percent == 0.0
        assert p.source == "SYSTEM"
        assert p.resolve() == 0.0

    def test_invalid_percent_rejected(self):
        with pytest.raises(ValueError, match="percent"):
            LossProfile(name="bad", percent=-1)
        with pytest.raises(ValueError, match="percent"):
            LossProfile(name="bad", percent=100)
        with pytest.raises(ValueError, match="percent"):
            LossProfile(name="bad", percent=100.0)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            LossProfile(name="  ", percent=5)

    def test_resolve_explicit_overrides_profile(self):
        p = LossProfile(name="spray", percent=15.0, source="USER")
        assert p.resolve(5.0) == 5.0
        assert p.resolve(None) == 15.0

    def test_resolve_rejects_invalid_explicit(self):
        p = LossProfile(name="spray", percent=15.0)
        with pytest.raises(ValueError, match="percent"):
            p.resolve(100)


class TestLossProfileIntegration:
    def test_profile_used_when_explicit_losses_absent(self):
        profile = LossProfile(name="airless", percent=20.0, source="USER")
        calc = SystemCalculator(loss_profile=profile)
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(obj, [LayerInput(make_primer(), 200)])
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 20.0
        # practical consumption must reflect 20% losses
        base = LayerCalculator.calculate(make_primer(), 200, losses_percent=0.0)
        k = calculate_loss_coefficient(20.0)
        assert result.layers[0].practical_consumption_l == pytest.approx(
            base.practical_consumption_l * k
        )

    def test_explicit_losses_override_profile(self):
        profile = LossProfile(name="airless", percent=20.0, source="USER")
        calc = SystemCalculator(loss_profile=profile)
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(
            obj, [LayerInput(make_primer(), 200, losses_percent=5.0)]
        )
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 5.0

    def test_layer_profile_overrides_calculator_profile(self):
        calc_profile = LossProfile(name="calc", percent=10.0)
        layer_profile = LossProfile(name="layer", percent=25.0)
        calc = SystemCalculator(loss_profile=calc_profile)
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(
            obj, [LayerInput(make_primer(), 200, loss_profile=layer_profile)]
        )
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 25.0

    def test_explicit_zero_overrides_profile(self):
        profile = LossProfile(name="airless", percent=20.0)
        calc = SystemCalculator(loss_profile=profile)
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(
            obj, [LayerInput(make_primer(), 200, losses_percent=0.0)]
        )
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 0.0

    def test_none_profile_yields_zero_losses(self):
        calc = SystemCalculator(loss_profile=LossProfile.none())
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(obj, [LayerInput(make_primer(), 200)])
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 0.0

    def test_no_profile_preserves_legacy_default_zero(self):
        calc = SystemCalculator()
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(obj, [LayerInput(make_primer(), 200)])
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 0.0

    def test_legacy_default_losses_still_works(self):
        calc = SystemCalculator(default_losses=12.0)
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(obj, [LayerInput(make_primer(), 200)])
        assert not validation.has_errors
        assert result.layers[0].losses_percent == 12.0

    def test_invalid_profile_percent_rejected_at_construction(self):
        with pytest.raises(ValueError):
            LossProfile(name="x", percent=150)

    def test_invalid_explicit_percent_rejected_at_resolve(self):
        calc = SystemCalculator(loss_profile=LossProfile(name="ok", percent=10))
        obj = ObjectData(area_m2=1.0)
        result, validation = calc.calculate(
            obj, [LayerInput(make_primer(), 200, losses_percent=100.0)]
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
        assert calc.resolve_losses(explicit_percent=7.0) == 7.0
        assert calc.resolve_losses(explicit_percent=None) == 30.0
        calc2 = SystemCalculator(default_losses=5.0)
        assert calc2.resolve_losses(explicit_percent=None) == 5.0
