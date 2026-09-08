"""
Двухступенчатый recommendation engine.

1. Жёсткий фильтр (rules)
2. Scoring 0–100 среди прошедших (scorer)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence, Callable

from app.domain.models import (
    CoatingSystem,
    ObjectData,
    Material,
    RecommendationItem,
    RecommendationResult,
    SystemCalculationResult,
)
from app.domain.calculator import SystemCalculator, LayerInput
from app.domain.recommendation.rules import filter_systems, FilterResult
from app.domain.recommendation.scorer import score_system, ScoreWeights, ScoreBreakdown


class RecommendationEngine:
    DISCLAIMER = (
        "\u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u043e\u0434\u0431\u043e\u0440 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u0410\u041a\u0417. \u041e\u043a\u043e\u043d\u0447\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0432\u044b\u0431\u043e\u0440 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e "
        "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0442\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u043e\u0439 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0435\u0439 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f, \u043f\u0440\u043e\u0435\u043a\u0442\u043d\u044b\u043c\u0438 "
        "\u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f\u043c\u0438 \u0438 \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u044b\u043c\u0438 \u043d\u043e\u0440\u043c\u0430\u0442\u0438\u0432\u043d\u044b\u043c\u0438 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043c\u0438."
    )

    def __init__(
        self,
        calculator: Optional[SystemCalculator] = None,
        weights: Optional[ScoreWeights] = None,
        materials_provider: Optional[Callable[[], dict[int, Material]]] = None,
    ):
        self.calculator = calculator or SystemCalculator()
        self.weights = weights or ScoreWeights()
        self.materials_provider = materials_provider

    def recommend(
        self,
        obj: ObjectData,
        systems: Sequence[CoatingSystem],
        calculate_costs: bool = True,
        top_n: int = 10,
        require_corrosion: bool = True,
        require_durability: bool = True,
    ) -> RecommendationResult:
        if not systems:
            return RecommendationResult(
                object_data=obj,
                insufficient_data=True,
                message="\u0412 \u0431\u0430\u0437\u0435 \u043d\u0435\u0442 \u0441\u0438\u0441\u0442\u0435\u043c \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u044f \u0434\u043b\u044f \u043f\u043e\u0434\u0431\u043e\u0440\u0430.",
                disclaimer=self.DISCLAIMER,
                created_at=datetime.now(),
            )

        filter_results = filter_systems(
            systems, obj,
            require_corrosion=require_corrosion,
            require_durability=require_durability,
        )
        passed = [fr for fr in filter_results if fr.passed]

        if not passed:
            fail_summary = []
            for fr in filter_results:
                if fr.reasons_fail:
                    fail_summary.append(f"\u00ab{fr.system.system_name}\u00bb: {fr.reasons_fail[0]}")
            return RecommendationResult(
                object_data=obj,
                items=[],
                insufficient_data=any(fr.insufficient_data for fr in filter_results),
                message=(
                    "\u041d\u0438 \u043e\u0434\u043d\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0435 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0437\u0430\u0434\u0430\u043d\u043d\u044b\u043c \u0443\u0441\u043b\u043e\u0432\u0438\u044f\u043c. "
                    + ("; ".join(fail_summary[:3]) if fail_summary else "")
                ),
                disclaimer=self.DISCLAIMER,
                created_at=datetime.now(),
            )

        materials_by_id: dict[int, Material] = {}
        if self.materials_provider:
            materials_by_id = self.materials_provider()

        calc_map: dict[int, SystemCalculationResult] = {}
        costs: list[float] = []

        if calculate_costs:
            for fr in passed:
                sys = fr.system
                try:
                    result, validation = self.calculator.calculate_from_system(
                        obj, sys, materials_by_id, skip_validation=True
                    )
                    if not validation.has_errors and result.layers:
                        calc_map[id(sys)] = result
                        costs.append(result.total_cost_per_m2)
                except Exception:
                    pass

        scored: list = []
        for fr in passed:
            calc = calc_map.get(id(fr.system))
            breakdown = score_system(
                filter_result=fr,
                obj=obj,
                calc_result=calc,
                all_costs=costs,
                weights=self.weights,
                compatibility_ok=True,
            )
            scored.append((fr, breakdown, calc))

        scored.sort(key=lambda x: x[1].total, reverse=True)

        items: list[RecommendationItem] = []
        for rank, (fr, breakdown, calc) in enumerate(scored[:top_n], start=1):
            items.append(
                RecommendationItem(
                    system=fr.system,
                    score=breakdown.total,
                    rank=rank,
                    reasons=breakdown.reasons,
                    warnings=breakdown.warnings,
                    limitations=breakdown.limitations,
                )
            )

        return RecommendationResult(
            object_data=obj,
            items=items,
            insufficient_data=False,
            message=f"\u041d\u0430\u0439\u0434\u0435\u043d\u043e \u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0445 \u0441\u0438\u0441\u0442\u0435\u043c: {len(passed)} \u0438\u0437 {len(systems)}",
            disclaimer=self.DISCLAIMER,
            created_at=datetime.now(),
        )

    def format_report(self, result: RecommendationResult) -> str:
        lines = [
            "\u2550\u2550\u2550 \u041f\u043e\u0434\u0431\u043e\u0440 \u0441\u0438\u0441\u0442\u0435\u043c \u0410\u041a\u0417 \u2550\u2550\u2550",
            f"\u041e\u0431\u044a\u0435\u043a\u0442: {result.object_data.object_name or '\u2014'}",
            f"\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f: {result.object_data.corrosion_category or '\u2014'}",
            f"\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c: {result.object_data.durability or '\u2014'}",
            f"\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435: {result.message}",
            "",
        ]
        if not result.items:
            lines.append("\u041f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0445 \u0441\u0438\u0441\u0442\u0435\u043c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
        else:
            for item in result.items:
                lines.append(f"{item.rank}. {item.system.system_name}  \u2014  {item.score:.0f}/100")
                for r in item.reasons[:4]:
                    lines.append(f"   \u2713 {r}")
                for w in item.warnings[:3]:
                    lines.append(f"   \u26a0 {w}")
                lines.append("")
        lines.append("\u2500" * 40)
        lines.append(result.disclaimer)
        return "\n".join(lines)
