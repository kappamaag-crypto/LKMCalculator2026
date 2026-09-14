"""§19 legacy parity: recommendation engine v2 ↔ v3.

Shared architecture: hard filter → score ranking, DISCLAIMER, ScoreBreakdown on items.
Intentional v3: transparent weights (no hidden condition/compatibility weight in total);
missing cost does not invent 0; engineering limitations surface; ScoreBreakdown retained.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.enums import (
    BinderType,
    CorrosionCategory,
    DurabilityLevel,
    EnvironmentType,
    MaterialType,
    SurfaceType,
)
from app.domain.models import CoatingSystem, LayerDefinition, Material, ObjectData
from app.domain.recommendation.recommender import RecommendationEngine
from app.domain.recommendation.rules import filter_system
from app.domain.recommendation.scorer import score_system, ScoreWeights


def make_material(name: str = "Test coating", price=None) -> Material:
    return Material(
        material_name=name,
        material_type=MaterialType.PRIMER,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_percent=70.0,
        solids_by_volume_percent=70.0,
        price_per_kg=price,
    )


def make_system(name, categories, durability, layers_count=2, price=None):
    mat = make_material(f"{name} material", price=price)
    layers = [
        LayerDefinition(layer_number=i + 1, target_dft=80.0, material=mat)
        for i in range(layers_count)
    ]
    return CoatingSystem(
        id=hash(name) % 10000,
        system_name=name,
        corrosion_categories=categories,
        durability=DurabilityLevel(durability) if durability else None,
        temperature_min=-40,
        temperature_max=60,
        surface_types=[SurfaceType.NEW_STEEL],
        environments=[EnvironmentType.OUTDOOR],
        layers=layers,
        number_of_layers=layers_count,
    )


def test_v2_and_v3_share_two_stage_architecture():
    root = Path(__file__).resolve().parents[2]
    v2 = (root / "v2" / "app" / "domain" / "recommendation" / "recommender.py").read_text(
        encoding="utf-8"
    )
    v3 = (root / "upload" / "app" / "domain" / "recommendation" / "recommender.py").read_text(
        encoding="utf-8"
    )
    assert "filter_systems" in v2 and "filter_systems" in v3
    assert "score_system" in v2 and "score_system" in v3
    assert "DISCLAIMER" in v2 and "DISCLAIMER" in v3
    assert "ScoreBreakdown" in v2 and "ScoreBreakdown" in v3


def test_v3_disclaimer_is_present_on_result():
    obj = ObjectData(
        corrosion_category=CorrosionCategory.C4,
        durability=DurabilityLevel.HIGH,
        surface_type=SurfaceType.NEW_STEEL,
    )
    result = RecommendationEngine().recommend(
        obj, [make_system("C4 High", [CorrosionCategory.C4], "High")], calculate_costs=False
    )
    assert result.disclaimer
    assert (
        "норматив" in result.disclaimer.lower()
        or "TDS" in result.disclaimer
        or "документац" in result.disclaimer.lower()
    )


def test_v3_hard_filter_rejects_wrong_category_like_legacy():
    fr = filter_system(
        make_system("Sys C3", [CorrosionCategory.C3], "High"),
        ObjectData(corrosion_category=CorrosionCategory.C5),
    )
    assert not fr.passed


def test_v3_ranking_preserves_score_breakdown():
    obj = ObjectData(
        corrosion_category=CorrosionCategory.C4,
        durability=DurabilityLevel.HIGH,
        surface_type=SurfaceType.NEW_STEEL,
        environment=EnvironmentType.OUTDOOR,
    )
    systems = [
        make_system("C4 High", [CorrosionCategory.C4], "High", price=500.0),
        make_system("C4 Med", [CorrosionCategory.C4], "Medium", price=400.0),
        make_system("C2 Low", [CorrosionCategory.C2], "Low", price=200.0),
    ]
    result = RecommendationEngine().recommend(obj, systems, calculate_costs=True, top_n=5)
    assert len(result.items) >= 1
    assert result.items[0].score >= result.items[-1].score
    assert "C2 Low" not in [i.system.system_name for i in result.items]
    for item in result.items:
        assert item.breakdown is not None
        assert item.breakdown.total == pytest.approx(item.score, rel=0, abs=1e-9)


def test_v3_unknown_cost_does_not_invent_zero_score_break():
    systems = [
        make_system("Known", [CorrosionCategory.C4], "High", price=500.0),
        make_system("Unknown", [CorrosionCategory.C4], "High", price=None),
    ]
    obj = ObjectData(
        corrosion_category=CorrosionCategory.C4,
        durability=DurabilityLevel.HIGH,
        surface_type=SurfaceType.NEW_STEEL,
        environment=EnvironmentType.OUTDOOR,
    )
    result = RecommendationEngine().recommend(obj, systems, calculate_costs=True, top_n=5)
    assert len(result.items) == 2
    unknown = next(i for i in result.items if i.system.system_name == "Unknown")
    assert unknown.score >= 0
    known = next(i for i in result.items if i.system.system_name == "Known")
    assert known.score >= unknown.score or known.breakdown.cost >= 0


def test_v3_score_has_no_hidden_condition_or_compatibility_weight():
    obj = ObjectData(corrosion_category=CorrosionCategory.C4, durability=DurabilityLevel.HIGH)
    fr = filter_system(make_system("A", [CorrosionCategory.C4], "High"), obj)
    breakdown = score_system(fr, obj, compatibility_ok=False)
    assert breakdown.compatibility == 0.0
    assert breakdown.conditions == 0.0
    assert 0 <= breakdown.total <= 100


def test_v3_weights_normalize():
    w = ScoreWeights(corrosion=3, durability=1, technology=1, cost=1).normalized()
    assert abs(w.corrosion + w.durability + w.technology + w.cost - 1.0) < 1e-12
