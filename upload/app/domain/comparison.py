"""
Сравнение систем покрытия.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from app.domain.models import (
    ObjectData,
    SystemCalculationResult,
    ComparisonResult,
)
from app.domain.calculator import SystemCalculator, LayerInput
from app.domain.validation import ValidationResult


@dataclass
class SystemCompareItem:
    """Система + её результат расчёта для сравнения."""

    name: str
    result: SystemCalculationResult
    validation: ValidationResult


class ComparisonEngine:
    """Сравнение 2–10 систем."""

    def __init__(self, calculator: SystemCalculator | None = None):
        self.calculator = calculator or SystemCalculator()

    def compare(
        self,
        obj: ObjectData,
        systems: Sequence[tuple[str, Sequence[LayerInput]]],
    ) -> ComparisonResult:
        """
        Сравнить несколько систем.

        systems: список (имя_системы, [LayerInput, ...])
        """
        if len(systems) < 2:
            raise ValueError("Для сравнения требуется не менее 2 систем")
        if len(systems) > 10:
            raise ValueError("Максимум 10 систем для сравнения")

        calc_results: list[SystemCalculationResult] = []
        for name, layer_inputs in systems:
            from app.domain.models import CoatingSystem
            sys = CoatingSystem(system_name=name)
            result, _ = self.calculator.calculate(obj, layer_inputs, system=sys)
            calc_results.append(result)

        comparison = ComparisonResult(
            object_data=obj,
            systems=calc_results,
            created_at=datetime.now(),
        )
        self._annotate(comparison)
        return comparison

    def compare_results(
        self,
        obj: ObjectData,
        results: Sequence[SystemCalculationResult],
    ) -> ComparisonResult:
        """Сравнить уже рассчитанные системы."""
        if len(results) < 2:
            raise ValueError("Для сравнения требуется не менее 2 систем")

        comparison = ComparisonResult(
            object_data=obj,
            systems=list(results),
            created_at=datetime.now(),
        )
        self._annotate(comparison)
        return comparison

    def _annotate(self, comparison: ComparisonResult) -> None:
        """Выделить лучшие/худшие по ключевым показателям."""
        systems = comparison.systems
        if not systems:
            return

        # Самая дешёвая / дорогая (по руб/м²)
        costs = [s.total_cost_per_m2 for s in systems]
        comparison.cheapest_index = costs.index(min(costs))
        comparison.most_expensive_index = costs.index(max(costs))

        # Самая тонкая / толстая
        dfts = [s.total_dft for s in systems]
        comparison.thinnest_index = dfts.index(min(dfts))
        comparison.thickest_index = dfts.index(max(dfts))

        # Минимум слоёв
        layer_counts = [len(s.layers) for s in systems]
        comparison.fewest_layers_index = layer_counts.index(min(layer_counts))

        # Лучший баланс цена/защита:
        # score = нормализованная толщина / нормализованная цена
        # (больше толщина при меньшей цене → лучше)
        max_dft = max(dfts) or 1.0
        max_cost = max(costs) or 1.0
        balance_scores = []
        for s in systems:
            norm_dft = s.total_dft / max_dft
            norm_cost = s.total_cost_per_m2 / max_cost if max_cost else 1.0
            # Чем выше толщина и ниже цена — тем лучше
            score = norm_dft / norm_cost if norm_cost > 0 else 0.0
            balance_scores.append(score)
        comparison.best_balance_index = balance_scores.index(max(balance_scores))

    def to_table(self, comparison: ComparisonResult) -> list[dict]:
        """
        Таблица сравнения для UI / Excel.

        Возвращает список строк: [{indicator, sys0, sys1, ...}, ...]
        """
        systems = comparison.systems
        n = len(systems)
        names = [s.system.system_name or f"Система {i+1}" for i, s in enumerate(systems)]

        def row(label: str, values: list, highlight_min: bool = False, highlight_max: bool = False) -> dict:
            r = {"indicator": label}
            for i, v in enumerate(values):
                r[f"sys_{i}"] = v
            if highlight_min and values:
                r["_min_idx"] = values.index(min(values))
            if highlight_max and values:
                r["_max_idx"] = values.index(max(values))
            return r

        rows = [
            row("Название", names),
            row("Количество слоёв", [len(s.layers) for s in systems], highlight_min=True),
            row("Общая толщина, мкм", [s.total_dft for s in systems], highlight_min=True, highlight_max=True),
            row("Расход, кг/м²", [s.total_practical_consumption_kg for s in systems], highlight_min=True),
            row("Расход, л/м²", [s.total_practical_consumption_l for s in systems], highlight_min=True),
            row("Стоимость, руб/м²", [s.total_cost_per_m2 for s in systems], highlight_min=True, highlight_max=True),
            row("Стоимость объекта, руб", [s.total_cost for s in systems], highlight_min=True),
            row(
                "Кол-во материала, кг",
                [sum(lr.total_consumption_kg for lr in s.layers) for s in systems],
            ),
        ]
        return rows