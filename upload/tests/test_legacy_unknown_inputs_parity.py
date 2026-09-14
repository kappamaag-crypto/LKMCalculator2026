"""§19 legacy parity: unknown / missing inputs.

v2 often fell back to 0.0 for missing prices (looks like free material).
v3 uses explicit None / validation errors / LossProfile DEFAULT provenance
instead of inventing commercial or physical values.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.domain.calculator import LayerCalculator, LayerInput, SystemCalculator
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData


def _mat(**kwargs) -> Material:
    base = dict(
        manufacturer="Parity",
        material_name="UnknownCase",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.25,
        solids_percent=55.0,
        solids_by_volume_percent=55.0,
    )
    base.update(kwargs)
    return Material(**base)


@pytest.fixture
def v2_layer_calc():
    root = Path(__file__).resolve().parents[2]
    if not (root / "v2" / "app" / "domain" / "calculator.py").exists():
        pytest.skip("v2 calculator baseline not present")
    saved = {k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")}
    saved_path = list(sys.path)
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = [str(root / "v2")] + [p for p in sys.path if "upload" not in p]
    from app.domain.calculator import LayerCalculator as V2LC
    from app.domain.models import Material as V2M
    from app.domain.enums import BinderType as V2BT, MaterialType as V2MT
    yield V2LC, V2M, V2BT, V2MT
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = saved_path
    sys.modules.update(saved)


def test_v3_missing_price_is_none_not_zero():
    layer = LayerCalculator.calculate(_mat(price_per_kg=None), target_dft=100, losses_percent=0)
    assert layer.cost_per_m2 is None
    assert layer.total_cost is None


def test_v2_missing_price_falls_back_to_zero(v2_layer_calc):
    V2LC, V2M, V2BT, V2MT = v2_layer_calc
    m = V2M(
        manufacturer="Parity",
        material_name="UnknownCase",
        material_type=V2MT.PRIMER_ENAMEL,
        binder_type=V2BT.EPOXY,
        density=1.25,
        solids_percent=55.0,
        price_per_kg=None,
    )
    layer = V2LC.calculate(m, target_dft=100, losses_percent=0)
    assert layer.cost_per_m2 == 0.0  # legacy fallback


def test_v3_system_total_cost_unknown_when_any_layer_price_missing():
    layers = [
        LayerInput(material=_mat(price_per_kg=100.0), target_dft=80, losses_percent=0),
        LayerInput(material=_mat(price_per_kg=None, material_name="NoPrice"), target_dft=100, losses_percent=0),
    ]
    result, validation = SystemCalculator().calculate(
        ObjectData(object_name="mix", area_m2=10.0), layers
    )
    assert not validation.has_errors
    assert result.total_cost_per_m2 is None
    assert result.total_cost is None


def test_v3_rejects_unknown_density():
    with pytest.raises(ValueError, match="плотность|Плотность"):
        LayerCalculator.calculate(_mat(density=0), target_dft=100, losses_percent=0)


def test_v3_rejects_unknown_solids_by_volume():
    with pytest.raises(ValueError, match="сухой остаток|сухого"):
        LayerCalculator.calculate(
            _mat(solids_by_volume_percent=0, solids_percent=0),
            target_dft=100,
            losses_percent=0,
        )


def test_v3_unspecified_losses_use_default_profile_provenance():
    result, validation = SystemCalculator().calculate(
        ObjectData(object_name="def", area_m2=1.0),
        [LayerInput(material=_mat(price_per_kg=100.0), target_dft=100, losses_percent=None)],
    )
    assert not validation.has_errors
    layer = result.layers[0]
    assert layer.losses_percent == 0.0
    assert getattr(layer, "losses_source", None) == "DEFAULT"
