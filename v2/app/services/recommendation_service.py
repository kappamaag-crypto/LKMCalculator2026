"""Application service: подбор систем АКЗ."""

from __future__ import annotations

from typing import Optional, Sequence, Callable

from app.domain.models import CoatingSystem, ObjectData, Material, RecommendationResult
from app.domain.recommendation import RecommendationEngine, ScoreWeights
from app.domain.calculator import SystemCalculator


class RecommendationService:
    def __init__(
        self,
        engine: Optional[RecommendationEngine] = None,
        weights: Optional[ScoreWeights] = None,
        materials_provider: Optional[Callable[[], dict[int, Material]]] = None,
    ):
        self.engine = engine or RecommendationEngine(
            weights=weights,
            materials_provider=materials_provider,
        )

    def recommend(
        self,
        obj: ObjectData,
        systems: Sequence[CoatingSystem],
        top_n: int = 5,
        calculate_costs: bool = True,
    ) -> RecommendationResult:
        return self.engine.recommend(
            obj=obj,
            systems=systems,
            top_n=top_n,
            calculate_costs=calculate_costs,
        )

    def format_report(self, result: RecommendationResult) -> str:
        return self.engine.format_report(result)