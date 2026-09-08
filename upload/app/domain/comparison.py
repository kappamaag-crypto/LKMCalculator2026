"""
Сравнение систем покрытия.

Сравнение не считает большую толщину автоматически лучшей защитой:
соответствие ISO 12944/ТДС должно быть подтверждено отдельно, а здесь
сопоставляются измеримые показатели расчёта — расход, стоимость, толщина
и количество слоёв.
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
        """Сравнить несколько систем."""
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
        """Выделить показатели без предположения, что большая DFT лучше."""
        systems = comparison.systems
        if not systems:
            return

        costs = [s.total_cost_per_m2 for s in systems]
        comparison.cheapest_index = costs.index(min(costs))
        comparison.most_expensive_index = costs.index(max(costs))

        dfts = [s.total_dft for s in systems]
        comparison.thinnest_index = dfts.index(min(dfts))
        comparison.thickest_index = dfts.index(max(dfts))

        layer_counts = [len(s.layers) for s in systems]
        comparison.fewest_layers_index = layer_counts.index(min(layer_counts))

        # "Лучший баланс" здесь означает только экономико-технологический баланс:
        # низкая стоимость и меньшее число слоёв. Толщина не является бонусом сама по себе.
        min_cost = min(costs)
        max_cost = max(costs)
        min_layers = min(layer_counts)
        max_layers = max(layer_counts)

        def normalize_inverse(value: float, low: float, high: float) -> float:
            if high == low:
                return 1.0
            return (high - value) / (high - low)

        balance_scores = []
        for cost, layers in zip(costs, layer_counts):
            cost_score = normalize_inverse(cost, min_cost, max_cost)
            layer_score = normalize_inverse(float(layers), float(min_layers), float(max_layers))
            # Цена важнее числа слоёв; итог 0..100.
            balance_scores.append(0.7 * cost_score + 0.3 * layer_score)

        comparison.best_balance_index = balance_scores.index(max(balance_scores))

    def to_table(self, comparison: ComparisonResult) -> list[dict]:
        """
        Таблица сравнения для UI / Excel.

        Включает общие показатели и подробности по каждому слою.
        """
        systems = comparison.systems
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
            row("Расход ЛКМ, кг/м²", [s.total_practical_consumption_kg for s in systems], highlight_min=True),
            row("Расход ЛКМ, л/м²", [s.total_practical_consumption_l for s in systems], highlight_min=True),
            row("Стоимость ЛКМ, руб/м²", [s.total_cost_per_m2 for s in systems], highlight_min=True, highlight_max=True),
            row("Стоимость объекта, руб", [s.total_cost for s in systems], highlight_min=True),
            row("Разбавитель, руб/м²", [s.total_thinner_cost / s.object_data.area_m2 if s.object_data.area_m2 > 0 else 0.0 for s in systems], highlight_min=True),
            row("Закупка ЛКМ, кг", [sum(lr.total_consumption_kg for lr in s.layers) for s in systems], highlight_min=True),
        ]

        max_layers = max((len(s.layers) for s in systems), default=0)
        for layer_no in range(max_layers):
            materials = []
            dfts = []
            consumptions = []
            costs = []
            for s in systems:
                if layer_no < len(s.layers):
                    lr = s.layers[layer_no]
                    materials.append(lr.material.display_name())
                    dfts.append(lr.target_dft)
                    consumptions.append(lr.practical_consumption_kg)
                    costs.append(lr.cost_per_m2 + lr.thinner_cost_per_m2)
                else:
                    materials.append("—")
                    dfts.append("—")
                    consumptions.append("—")
                    costs.append("—")
            rows.extend([
                row(f"Слой {layer_no + 1}: материал", materials),
                row(f"Слой {layer_no + 1}: DFT, мкм", dfts),
                row(f"Слой {layer_no + 1}: расход, кг/м²", consumptions),
                row(f"Слой {layer_no + 1}: стоимость, руб/м²", costs),
            ])

        return rows
