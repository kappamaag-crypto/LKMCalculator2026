"""Тесты recommendation engine."""

from __future__ import annotations

from app.domain.models import CoatingSystem, LayerDefinition, ObjectData, Material
from app.domain.enums import CorrosionCategory, DurabilityLevel, SurfaceType, EnvironmentType, MaterialType, BinderType
from app.domain.recommendation.rules import filter_system, filter_systems
from app.domain.recommendation.scorer import score_system, ScoreWeights
from app.domain.recommendation.recommender import RecommendationEngine
from app.domain.recommendation.rules import FilterResult


def _sys(name, cats, dur, layers=2):
    mats = Material(material_name="M", material_type=MaterialType.PRIMER_ENAMEL, binder_type=BinderType.EPOXY, density=1.4, solids_percent=70)
    return CoatingSystem(
        system_name=name,
        corrosion_categories=cats,
        durability=dur,
        surface_types=[SurfaceType.NEW_STEEL],
        environments=[EnvironmentType.OUTDOOR],
        temperature_min=-40, temperature_max=80,
        layers=[LayerDefinition(material=mats, layer_number=i+1, target_dft=100) for i in range(layers)],
        number_of_layers=layers,
    )


def test_filter_pass():
    sys = _sys("C4-High", [CorrosionCategory.C4], DurabilityLevel.HIGH)
    obj = ObjectData(corrosion_category=CorrosionCategory.C4, durability=DurabilityLevel.HIGH)
    fr = filter_system(sys, obj)
    assert fr.passed


def test_filter_fail_category():
    sys = _sys("C2", [CorrosionCategory.C2], DurabilityLevel.MEDIUM)
    obj = ObjectData(corrosion_category=CorrosionCategory.C5, durability=DurabilityLevel.MEDIUM)
    fr = filter_system(sys, obj)
    assert not fr.passed


def test_recommender_ranks():
    systems = [
        _sys("C4-Med", [CorrosionCategory.C4], DurabilityLevel.MEDIUM, layers=2),
        _sys("C4-High", [CorrosionCategory.C4, CorrosionCategory.C5], DurabilityLevel.HIGH, layers=3),
        _sys("C2-Low", [CorrosionCategory.C2], DurabilityLevel.LOW, layers=1),
    ]
    obj = ObjectData(
        object_name="Test",
        corrosion_category=CorrosionCategory.C4,
        durability=DurabilityLevel.MEDIUM,
        surface_type=SurfaceType.NEW_STEEL,
        environment=EnvironmentType.OUTDOOR,
        temperature_min=-20, temperature_max=40,
    )
    result = RecommendationEngine().recommend(obj, systems, calculate_costs=False, top_n=5)
    assert len(result.items) >= 1
    assert result.items[0].score >= result.items[-1].score if len(result.items) > 1 else True
    assert all(item.score >= 0 for item in result.items)
