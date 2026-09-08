"""Двухступенчатый recommendation engine: hard filter → score."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Sequence, Callable

from app.domain.models import CoatingSystem, ObjectData, Material, RecommendationItem, RecommendationResult, SystemCalculationResult
from app.domain.calculator import SystemCalculator
from app.domain.recommendation.rules import filter_systems, FilterResult
from app.domain.recommendation.scorer import score_system, ScoreWeights, ScoreBreakdown

logger = logging.getLogger(__name__)


class RecommendationEngine:
    DISCLAIMER = (
        "Предварительный подбор системы АКЗ. Окончательный выбор необходимо "
        "подтвердить технической документацией производителя, проектными "
        "требованиями и применимыми нормативными документами."
    )

    def __init__(self, calculator: Optional[SystemCalculator] = None, weights: Optional[ScoreWeights] = None, materials_provider: Optional[Callable[[], dict[int, Material]]] = None):
        self.calculator = calculator or SystemCalculator()
        self.weights = weights or ScoreWeights()
        self.materials_provider = materials_provider

    def recommend(self, obj: ObjectData, systems: Sequence[CoatingSystem], calculate_costs: bool = True, top_n: int = 10, require_corrosion: bool = True, require_durability: bool = True) -> RecommendationResult:
        if not systems:
            return RecommendationResult(object_data=obj, insufficient_data=True, message="В базе нет систем покрытия для подбора.", disclaimer=self.DISCLAIMER)

        filter_results = filter_systems(systems, obj, require_corrosion=require_corrosion, require_durability=require_durability)
        passed = [fr for fr in filter_results if fr.passed]
        if not passed:
            fail_summary = [f"«{fr.system.system_name}»: {fr.reasons_fail[0]}" for fr in filter_results if fr.reasons_fail]
            return RecommendationResult(
                object_data=obj,
                items=[],
                insufficient_data=any(fr.insufficient_data for fr in filter_results),
                message="Ни одна система не соответствует заданным условиям. " + ("; ".join(fail_summary[:3]) if fail_summary else ""),
                disclaimer=self.DISCLAIMER,
            )

        materials_by_id: dict[int, Material] = self.materials_provider() if self.materials_provider else {}
        calc_map: dict[int, SystemCalculationResult] = {}
        costs: list[float] = []

        if calculate_costs:
            for fr in passed:
                try:
                    calc_result, validation = self.calculator.calculate_from_system(obj, fr.system, materials_by_id, skip_validation=True)
                    if not validation.has_errors and calc_result.layers:
                        calc_map[id(fr.system)] = calc_result
                        costs.append(calc_result.total_cost_per_m2)
                    else:
                        logger.warning("Не удалось получить валидный расчёт стоимости для системы %r", fr.system.system_name)
                except Exception:
                    logger.exception("Ошибка расчёта стоимости для системы %r", fr.system.system_name)

        scored: list[tuple[FilterResult, ScoreBreakdown, Optional[SystemCalculationResult]]] = []
        for fr in passed:
            calc = calc_map.get(id(fr.system))
            breakdown = score_system(filter_result=fr, obj=obj, calc_result=calc, all_costs=costs, weights=self.weights, compatibility_ok=True)
            scored.append((fr, breakdown, calc))
        scored.sort(key=lambda x: x[1].total, reverse=True)

        items: list[RecommendationItem] = []
        for rank, (fr, breakdown, calc) in enumerate(scored[:top_n], start=1):
            items.append(RecommendationItem(system=fr.system, score=breakdown.total, rank=rank, status=getattr(breakdown, "status", "Подходит"), reasons=breakdown.reasons, warnings=breakdown.warnings, limitations=breakdown.limitations))

        return RecommendationResult(object_data=obj, items=items, insufficient_data=False, message=f"Найдено подходящих систем: {len(passed)} из {len(systems)}", disclaimer=self.DISCLAIMER)

    def format_report(self, result: RecommendationResult) -> str:
        lines = [
            "═══ Подбор систем АКЗ ═══",
            f"Объект: {result.object_data.object_name or '—'}",
            f"Категория: {result.object_data.corrosion_category or '—'}",
            f"Долговечность: {result.object_data.durability or '—'}",
            f"Сообщение: {result.message}",
            "",
        ]
        if not result.items:
            lines.append("Подходящих систем не найдено.")
            if result.insufficient_data:
                lines.append("⚠ Недостаточно данных для рекомендации.")
        else:
            for item in result.items:
                lines.append(f"{item.rank}. {item.system.system_name} — {item.score:.0f}/100")
                for reason in item.reasons[:4]:
                    lines.append(f"   ✓ {reason}")
                for warning in item.warnings[:3]:
                    lines.append(f"   ⚠ {warning}")
                for limitation in item.limitations[:3]:
                    lines.append(f"   ℹ {limitation}")
                lines.append("")
        lines.append("─" * 40)
        lines.append(result.disclaimer)
        return "\n".join(lines)
