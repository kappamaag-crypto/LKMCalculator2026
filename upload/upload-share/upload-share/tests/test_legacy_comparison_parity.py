"""§19 legacy parity: ComparisonEngine v2 ↔ v3.

Shared: 2–N systems, annotate cheapest/most_expensive/thinnest/thickest/fewest_layers,
transparent to_table rows. Intentional v3 changes:
- no derived «best balance» score (best_balance_index always None);
- cheapest/most_expensive ignore systems with total_cost_per_m2=None (UNKNOWN price);
- max 10 systems; compare_results rejects mixed object areas.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.domain.calculator import LayerInput, SystemCalculator
from app.domain.comparison import ComparisonEngine
from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material, ObjectData


def _mat(name: str, *, density: float, sv: float, price) -> Material:
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


@pytest.fixture
def v2_engine():
    root = Path(__file__).resolve().parents[2]
    if not (root / "v2" / "app" / "domain" / "comparison.py").exists():
        pytest.skip("v2 comparison baseline not present")
    saved = {k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")}
    saved_path = list(sys.path)
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = [str(root / "v2")] + [p for p in sys.path if "upload" not in p]
    from app.domain.comparison import ComparisonEngine as V2CE
    from app.domain.calculator import LayerInput as V2LI, SystemCalculator as V2SC
    from app.domain.models import Material as V2M, ObjectData as V2O
    from app.domain.enums import BinderType as V2BT, MaterialType as V2MT
    yield {
        "ComparisonEngine": V2CE,
        "LayerInput": V2LI,
        "SystemCalculator": V2SC,
        "Material": V2M,
        "ObjectData": V2O,
        "BinderType": V2BT,
        "MaterialType": V2MT,
    }
    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    sys.path = saved_path
    sys.modules.update(saved)


def test_v3_rejects_less_than_two_and_more_than_ten():
    eng = ComparisonEngine()
    obj = ObjectData(object_name="x", area_m2=10.0)
    layers = [LayerInput(material=_mat("A", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0)]
    with pytest.raises(ValueError):
        eng.compare(obj, [("only", layers)])
    too_many = [(f"s{i}", layers) for i in range(11)]
    with pytest.raises(ValueError):
        eng.compare(obj, too_many)


def test_v3_cheapest_among_known_prices_only():
    obj = ObjectData(object_name="c", area_m2=10.0)
    cheap = [LayerInput(material=_mat("Cheap", density=1.0, sv=50.0, price=50.0), target_dft=100, losses_percent=0)]
    dear = [LayerInput(material=_mat("Dear", density=1.0, sv=50.0, price=200.0), target_dft=100, losses_percent=0)]
    unknown = [LayerInput(material=_mat("Unk", density=1.0, sv=50.0, price=None), target_dft=100, losses_percent=0)]
    cmp = ComparisonEngine().compare(obj, [("u", unknown), ("c", cheap), ("d", dear)])
    assert cmp.systems[0].total_cost_per_m2 is None
    assert cmp.cheapest_index == 1
    assert cmp.most_expensive_index == 2
    assert cmp.best_balance_index is None


def test_v3_and_v2_agree_on_dft_and_layer_extrema(v2_engine):
    """Binary-friendly inputs: DFT / layer-count extrema match across versions."""
    area = 10.0
    obj = ObjectData(object_name="p", area_m2=area)
    thin = [LayerInput(material=_mat("T", density=1.0, sv=50.0, price=100.0), target_dft=50, losses_percent=0)]
    thick = [
        LayerInput(material=_mat("A", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0),
        LayerInput(material=_mat("B", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0),
    ]
    v3 = ComparisonEngine().compare(obj, [("thin", thin), ("thick", thick)])
    assert v3.thinnest_index == 0
    assert v3.thickest_index == 1
    assert v3.fewest_layers_index == 0
    assert v3.cheapest_index == 0
    assert v3.best_balance_index is None

    V2 = v2_engine

    def v2m(name, dft_price=100.0):
        return V2["Material"](
            manufacturer="Parity",
            material_name=name,
            material_type=V2["MaterialType"].PRIMER_ENAMEL,
            binder_type=V2["BinderType"].EPOXY,
            density=1.0,
            solids_percent=50.0,
            price_per_kg=dft_price,
        )

    v2_obj = V2["ObjectData"](object_name="p", area_m2=area)
    v2_thin = [V2["LayerInput"](material=v2m("T"), target_dft=50, losses_percent=0)]
    v2_thick = [
        V2["LayerInput"](material=v2m("A"), target_dft=100, losses_percent=0),
        V2["LayerInput"](material=v2m("B"), target_dft=100, losses_percent=0),
    ]
    v2 = V2["ComparisonEngine"]().compare(v2_obj, [("thin", v2_thin), ("thick", v2_thick)])
    assert v2.thinnest_index == 0
    assert v2.thickest_index == 1
    assert v2.fewest_layers_index == 0
    assert v2.cheapest_index == 0
    assert getattr(v2, "best_balance_index", None) is not None
    assert v3.best_balance_index is None


def test_v3_to_table_includes_core_indicators():
    obj = ObjectData(object_name="t", area_m2=5.0)
    s1 = [LayerInput(material=_mat("A", density=1.0, sv=50.0, price=100.0), target_dft=100, losses_percent=0)]
    s2 = [LayerInput(material=_mat("B", density=1.0, sv=50.0, price=150.0), target_dft=120, losses_percent=0)]
    cmp = ComparisonEngine().compare(obj, [("S1", s1), ("S2", s2)])
    rows = ComparisonEngine().to_table(cmp)
    indicators = [r["indicator"] for r in rows]
    assert "Общая толщина, мкм" in indicators or any("толщина" in i.lower() for i in indicators)
    assert any("Стоимость" in i or "стоимость" in i for i in indicators)
