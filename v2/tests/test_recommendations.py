"""Тесты recommendation engine."""

from __future__ import annotations

import pytest

from app.domain.models import (
    CoatingSystem,
    LayerDefinition,
    ObjectData,
    Material,
)
from app.domain.enums import (
    CorrosionCategory,
    DurabilityLevel,
    SurfaceType,
    EnvironmentType,
    MaterialType,
    BinderType,
)
from app.domain.recommendation.rules import filter_system, filter_systems
from app.domain.recommendation.scorer import score_system, ScoreWeights
from app.domain.recommendation.recommender import RecommendationEngine
from app.domain.recommendation.rules import FilterResult


def make_system(
    name: str,
    categories: list,
    durability: str | None,
    layers_count: int = 2,
    t_min: float | None = -40,
    t_max: float | None = 60,
    surfaces: list | None = None,
) -> CoatingSystem:
    layers = [
        LayerDefinition(layer_number=i + 1, target_dft=80.0)
        for i in range(layers_count)
    ]
    return CoatingSystem(
        id=hash(name) % 10000,
        system_name=name,
        corrosion_categories=categories,
        durability=DurabilityLevel(durability) if durability else None,
        temperature_min=t_min,
        temperature_max=t_max,
        surface_types=surfaces or [SurfaceType.NEW_STEEL],
        environments=[EnvironmentType.OUTDOOR],
        layers=layers,
        number_of_layers=layers_count,
    )


class TestFilter:
    def test_pass_c4_high(self):
        sys = make_system("Sys C4 High", [CorrosionCategory.C4], "High")
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.HIGH,
            surface_type=SurfaceType.NEW_STEEL,
        )
        fr = filter_system(sys, obj)
        assert fr.passed
        assert any("C4" in r for r in fr.reasons_pass)

    def test_fail_wrong_category(self):
        sys = make_system("Sys C3", [CorrosionCategory.C3], "High")
        obj = ObjectData(corrosion_category=CorrosionCategory.C5)
        fr = filter_system(sys, obj)
        assert not fr.passed
        assert any("C5" in r for r in fr.reasons_fail)

    def test_fail_low_durability(self):
        sys = make_system("Sys Low", [CorrosionCategory.C4], "Low")
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.HIGH,
        )
        fr = filter_system(sys, obj)
        assert not fr.passed

    def test_insufficient_data(self):
        sys = make_system("Empty", [], None)
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.HIGH,
        )
        fr = filter_system(sys, obj, require_corrosion=True, require_durability=True)
        assert not fr.passed
        assert fr.insufficient_data

    def test_temperature_fail(self):
        sys = make_system("Temp", [CorrosionCategory.C3], "Medium", t_min=-20, t_max=40)
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C3,
            durability=DurabilityLevel.MEDIUM,
            temperature_min=-40,
            temperature_max=60,
        )
        fr = filter_system(sys, obj)
        assert not fr.passed


class TestScorer:
    def test_score_range(self):
        sys = make_system("Good", [CorrosionCategory.C4], "High")
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.HIGH,
        )
        fr = filter_system(sys, obj)
        assert fr.passed
        br = score_system(fr, obj)
        assert 0 <= br.total <= 100

    def test_higher_durability_better(self):
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.MEDIUM,
        )
        sys_med = make_system("Med", [CorrosionCategory.C4], "Medium")
        sys_high = make_system("High", [CorrosionCategory.C4], "High")
        fr_m = filter_system(sys_med, obj)
        fr_h = filter_system(sys_high, obj)
        score_m = score_system(fr_m, obj).total
        score_h = score_system(fr_h, obj).total
        assert score_h >= score_m


class TestRecommender:
    def test_recommend_ranking(self):
        systems = [
            make_system("C3 Medium", [CorrosionCategory.C3], "Medium"),
            make_system("C4 High", [CorrosionCategory.C4, CorrosionCategory.C5], "High"),
            make_system("C4 Medium", [CorrosionCategory.C4], "Medium"),
            make_system("C2 Low", [CorrosionCategory.C2], "Low"),
        ]
        obj = ObjectData(
            object_name="Мост",
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.MEDIUM,
            surface_type=SurfaceType.NEW_STEEL,
            environment=EnvironmentType.OUTDOOR,
        )
        engine = RecommendationEngine()
        result = engine.recommend(obj, systems, calculate_costs=False, top_n=5)

        assert len(result.items) >= 1
        assert result.items[0].score >= result.items[-1].score
        # C2 не должна пройти
        names = [i.system.system_name for i in result.items]
        assert "C2 Low" not in names
        assert result.disclaimer

    def test_no_match(self):
        systems = [make_system("C1", [CorrosionCategory.C1], "Low")]
        obj = ObjectData(
            corrosion_category=CorrosionCategory.C5,
            durability=DurabilityLevel.HIGH,
        )
        engine = RecommendationEngine()
        result = engine.recommend(obj, systems, calculate_costs=False)
        assert len(result.items) == 0
        assert "Ни одна система" in result.message or result.message

    def test_empty_catalog(self):
        engine = RecommendationEngine()
        result = engine.recommend(ObjectData(), [], calculate_costs=False)
        assert result.insufficient_data
        assert len(result.items) == 0

    def test_report_format(self):
        systems = [make_system("C4 High", [CorrosionCategory.C4], "High")]
        obj = ObjectData(
            object_name="Резервуар",
            corrosion_category=CorrosionCategory.C4,
            durability=DurabilityLevel.HIGH,
        )
        engine = RecommendationEngine()
        result = engine.recommend(obj, systems, calculate_costs=False)
        report = engine.format_report(result)
        assert "Подбор систем АКЗ" in report
        assert "C4 High" in report
        assert "Предварительный подбор" in report