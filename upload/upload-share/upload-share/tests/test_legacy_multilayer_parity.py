"""§19 legacy parity: multilayer system calculation v2 ↔ v3.

Aggregation is the sum of per-layer results on a common area. Clean binary-friendly
inputs match numerically across versions. Cases with intermediate rounding in v2
diverge intentionally (v3 keeps full float precision).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.domain.calculator import LayerInput, SystemCalculator
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData


def _v3_material(name: str, *, density: float, sv: float, price: float) -> Material:
    return Material(
        manufacturer="Parity",
        material_name=name,
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=density,
        solids_percent=sv,
        solids_by_volume_percent=sv,
        price_per_kg=price,
    )


def _load_v2_modules():
    root = Path(__file__).resolve().parents[2]
    v2_root = root / "v2"
    if not (v2_root / "app" / "domain" / "calculator.py").exists():
        pytest.skip("v2 calculator baseline not present")
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path.insert(0, str(v2_root))
    from app.domain.models import Material as V2Material, ObjectData as V2ObjectData
    from app.domain.calculator import LayerInput as V2LayerInput, SystemCalculator as V2SystemCalculator
    from app.domain.enums import BinderType as V2BinderType, MaterialType as V2MaterialType
    return {
        "Material": V2Material,
        "ObjectData": V2ObjectData,
        "LayerInput": V2LayerInput,
        "SystemCalculator": V2SystemCalculator,
        "BinderType": V2BinderType,
        "MaterialType": V2MaterialType,
    }


@pytest.fixture
def v2():
    root = Path(__file__).resolve().parents[2]
    saved_modules = {k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")}
    saved_path = list(sys.path)
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = [str(root / "v2")] + [p for p in sys.path if "upload" not in p]
    mods = _load_v2_modules()
    yield mods
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = saved_path
    sys.modules.update(saved_modules)


def test_v3_multilayer_totals_match_independent_algebra():
    area = 12.5
    layers = [
        LayerInput(material=_v3_material("L1", density=1.25, sv=55.0, price=200.0), target_dft=80, losses_percent=10),
        LayerInput(material=_v3_material("L2", density=1.40, sv=60.0, price=250.0), target_dft=120, losses_percent=20),
        LayerInput(material=_v3_material("L3", density=1.10, sv=50.0, price=180.0), target_dft=50, losses_percent=5),
    ]
    result, validation = SystemCalculator().calculate(
        ObjectData(object_name="multi", area_m2=area), layers
    )
    assert not validation.has_errors

    exp_dft = sum(li.target_dft for li in layers)
    exp_l = exp_kg = exp_cost_m2 = 0.0
    for li in layers:
        base_l = (li.target_dft * 100.0 / li.material.solids_by_volume_percent) / 1000.0
        pract_l = base_l * 100.0 / (100.0 - li.losses_percent)
        pract_kg = pract_l * li.material.density
        exp_l += pract_l
        exp_kg += pract_kg
        exp_cost_m2 += pract_kg * li.material.price_per_kg

    assert result.total_dft == pytest.approx(exp_dft, rel=1e-13, abs=1e-14)
    assert result.total_practical_consumption_l == pytest.approx(exp_l, rel=1e-13, abs=1e-14)
    assert result.total_practical_consumption_kg == pytest.approx(exp_kg, rel=1e-13, abs=1e-14)
    assert result.total_cost_per_m2 == pytest.approx(exp_cost_m2, rel=1e-13, abs=1e-14)
    assert result.total_cost == pytest.approx(exp_cost_m2 * area, rel=1e-13, abs=1e-14)
    assert len(result.layers) == 3


def test_v2_v3_multilayer_match_on_binary_friendly_inputs(v2):
    """No intermediate-rounding drift: SV=50, dens=1, losses=0."""
    area = 10.0
    V2M, V2O, V2LI, V2SC = v2["Material"], v2["ObjectData"], v2["LayerInput"], v2["SystemCalculator"]
    V2MT, V2BT = v2["MaterialType"], v2["BinderType"]

    def v2_mat(name):
        return V2M(
            manufacturer="Parity",
            material_name=name,
            material_type=V2MT.PRIMER_ENAMEL,
            binder_type=V2BT.EPOXY,
            density=1.0,
            solids_percent=50.0,
            price_per_kg=100.0,
        )

    v2_layers = [
        V2LI(material=v2_mat("A"), target_dft=100, losses_percent=0),
        V2LI(material=v2_mat("B"), target_dft=100, losses_percent=0),
    ]
    v2_result, v2_val = V2SC().calculate(V2O(object_name="t", area_m2=area), v2_layers)
    assert not v2_val.issues

    v3_layers = [
        LayerInput(material=_v3_material("A", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0),
        LayerInput(material=_v3_material("B", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0),
    ]
    v3_result, v3_val = SystemCalculator().calculate(
        ObjectData(object_name="t", area_m2=area), v3_layers
    )
    assert not v3_val.has_errors

    assert v3_result.total_dft == v2_result.total_dft == 200.0
    assert v3_result.total_practical_consumption_l == pytest.approx(
        v2_result.total_practical_consumption_l, rel=0, abs=0
    )
    assert v3_result.total_practical_consumption_kg == pytest.approx(
        v2_result.total_practical_consumption_kg, rel=0, abs=0
    )
    assert v3_result.total_cost_per_m2 == pytest.approx(v2_result.total_cost_per_m2, rel=0, abs=0)
    assert v3_result.total_cost == pytest.approx(v2_result.total_cost_per_m2 * area, rel=1e-12, abs=1e-12)


def test_v3_multilayer_rejects_invalid_losses_via_validation():
    layers = [
        LayerInput(
            material=_v3_material("X", density=1.0, sv=50.0, price=100.0),
            target_dft=100,
            losses_percent=100,
        )
    ]
    result, validation = SystemCalculator().calculate(
        ObjectData(object_name="bad", area_m2=1.0), layers
    )
    assert validation.has_errors
    assert any("LOSSES" in (issue.code or "") for issue in validation.issues)
