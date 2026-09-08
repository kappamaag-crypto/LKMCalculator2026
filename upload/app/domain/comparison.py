"""
Сравнение систем покрытия.

Сравнение сопоставляет расчётные показатели: расход, стоимость, толщину
и количество слоёв. Закупка, фасовка, остатки и складские показатели
в расчёт не входят.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from app.domain.models import ObjectData, SystemCalculationResult, ComparisonResult
from app.domain.calculator import SystemCalculator, LayerInput
from app.domain.validation import ValidationResult


class ComparisonEngine:
    """Сравнение 2–10 систем."""

    def __init__(self, calculator: SystemCalculator | None = None):
        self.calculator = calculator or SystemCalculator()

    def compare(
        self,
        obj: ObjectData,
        systems: Sequence[tuple[str, Sequence[LayerInput]]],
    ) -> ComparisonResult:
        if len(systems) < 2:
            raise ValueError("Для сравнения требуется не менее 2 систем")
        if len(systems) > 10:
            raise ValueError("Максимум 10 систем для сравнения")

        from app.domain.models import CoatingSystem

        results: list[SystemCalculationResult] = []
        for name, layer_inputs in systems:
            result, _ = self.calculator.calculate(
                obj, layer_inputs, system=CoatingSystem(system_name=name)
            )
            results.append(result)

        comparison = ComparisonResult(
            object_data=obj,
            systems=results,
            created_at=datetime.now(),
        )
        self._annotate(comparison)
        return comparison

    def compare_results(
        self,
        obj: ObjectData,
        results: Sequence[SystemCalculationResult],
    ) -> ComparisonResult:
        if len(results) < 2:
            raise ValueError("Для сравнения требуется не менее 2 систем")
        comparison = ComparisonResult(
            object_data=obj,
            systems=list(results),
            created_at=datetime.now(),
        )
        self._annotate(comparison)
        return comparison

    @staticmethod
    def _known_costs(systems: Sequence[SystemCalculationResult]) -> list[tuple[int, float]]:
        return [
            (i, s.total_cost_per_m2)
            for i, s in enumerate(systems)
            if s.total_cost_per_m2 is not None
        ]

    def _annotate(self, comparison: ComparisonResult) -> None:
        systems = comparison.systems
        if not systems:
            return

        known_costs = self._known_costs(systems)
        if known_costs:
            cheapest = min(known_costs, key=lambda x: x[1])
            expensive = max(known_costs, key=lambda x: x[1])
            comparison.cheapest_index = cheapest[0]
            comparison.most_expensive_index = expensive[0]
        else:
            comparison.cheapest_index = None
            comparison.most_expensive_index = None

        dfts = [s.total_dft for s in systems]
        comparison.thinnest_index = dfts.index(min(dfts))
        comparison.thickest_index = dfts.index(max(dfts))

        layer_counts = [len(s.layers) for s in systems]
        comparison.fewest_layers_index = layer_counts.index(min(layer_counts))

        if known_costs:
            min_cost = min(v for _, v in known_costs)
            max_cost = max(v for _, v in known_costs)
            min_layers = min(layer_counts)
            max_layers = max(layer_counts)

            def normalize_inverse(value: float, low: float, high: float) -> float:
                if high == low:
                    return 1.0
                return (high - value) / (high - low)

            scores: list[tuple[int, float]] = []
            for index, cost in known_costs:
                cost_score = normalize_inverse(cost, min_cost, max_cost)
                layer_score = normalize_inverse(
                    float(layer_counts[index]), float(min_layers), float(max_layers)
                )
                scores.append((index, 0.7 * cost_score + 0.3 * layer_score))
            comparison.best_balance_index = max(scores, key=lambda x: x[1])[0]
        else:
            comparison.best_balance_index = None

    def to_table(self, comparison: ComparisonResult) -> list[dict]:
        systems = comparison.systems
        names = [s.system.system_name or f"Система {i + 1}" for i, s in enumerate(systems)]

        def row(label: str, values: list, highlight_min: bool = False, highlight_max: bool = False) -> dict:
            result = {"indicator": label}
            for i, value in enumerate(values):
                result[f"sys_{i}"] = value
            numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if highlight_min and numeric:
                min_value = min(numeric)
                result["_min_idx"] = values.index(min_value)
            if highlight_max and numeric:
                max_value = max(numeric)
                result["_max_idx"] = values.index(max_value)
            return result

        thinner_costs = []
        for s in systems:
            if s.total_thinner_cost is None or not s.object_data.area_m2 or s.object_data.area_m2 <= 0:
                thinner_costs.append(None)
            else:
                thinner_costs.append(s.total_thinner_cost / s.object_data.area_m2)

        rows = [
            row("Название", names),
            row("Количество слоёв", [len(s.layers) for s in systems], highlight_min=True),
            row("Общая толщина, мкм", [s.total_dft for s in systems], highlight_min=True, highlight_max=True),
            row("Расход ЛКМ, кг/м²", [s.total_practical_consumption_kg for s in systems], highlight_min=True),
            row("Расход ЛКМ, л/м²", [s.total_practical_consumption_l for s in systems], highlight_min=True),
            row("Стоимость ЛКМ + разбавителя, руб/м²", [s.total_cost_per_m2 for s in systems], highlight_min=True, highlight_max=True),
            row("Стоимость объекта, руб", [s.total_cost for s in systems], highlight_min=True),
            row("Стоимость разбавителя, руб/м²", thinner_costs, highlight_min=True),
        ]

        max_layers = max((len(s.layers) for s in systems), default=0)
        for layer_no in range(max_layers):
            materials, dfts, consumptions, costs = [], [], [], []
            for s in systems:
                if layer_no < len(s.layers):
                    lr = s.layers[layer_no]
                    materials.append(lr.material.display_name())
                    dfts.append(lr.target_dft)
                    consumptions.append(lr.practical_consumption_kg)
                    costs.append(
                        lr.cost_per_m2 + lr.thinner_cost_per_m2
                        if lr.cost_per_m2 is not None and lr.thinner_cost_per_m2 is not None
                        else None
                    )
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
