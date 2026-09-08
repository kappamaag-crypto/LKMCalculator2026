"""Application service: расчёты и сравнение."""

from __future__ import annotations

from typing import Optional, Sequence

from app.domain.models import (
    Material,
    ObjectData,
    CoatingSystem,
    SystemCalculationResult,
    ComparisonResult,
)
from app.domain.calculator import SystemCalculator, LayerInput, LayerCalculator
from app.domain.comparison import ComparisonEngine
from app.domain.validation import ValidationResult


class CalculationService:
    """
    Сервис расчётов.

    Оркестрирует calculator + validation + (опционально) репозитории.
    Инженерные формулы остаются в domain/calculator.py и domain/formulas.py.
    """

    def __init__(
        self,
        calculator: Optional[SystemCalculator] = None,
        comparison_engine: Optional[ComparisonEngine] = None,
        default_losses: float = 0.0,
    ):
        self.calculator = calculator or SystemCalculator(default_losses=default_losses)
        self.comparison = comparison_engine or ComparisonEngine(self.calculator)

    def calculate_layer(
        self,
        material: Material,
        target_dft: float,
        losses_percent: float = 0.0,
        thinner_percent: float = 0.0,
        thinner: Optional[Material] = None,
        thinner_basis: Optional[str] = None,
        area_m2: float = 1.0,
    ):
        return LayerCalculator.calculate(
            material=material,
            target_dft=target_dft,
            losses_percent=losses_percent,
            thinner_percent=thinner_percent,
            thinner=thinner,
            thinner_basis=thinner_basis,
            area_m2=area_m2,
        )

    def calculate_system(
        self,
        obj: ObjectData,
        layers: Sequence[LayerInput],
        system: Optional[CoatingSystem] = None,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        return self.calculator.calculate(obj, layers, system=system)

    def calculate_from_template(
        self,
        obj: ObjectData,
        system: CoatingSystem,
        materials_by_id: dict[int, Material],
        losses_percent: float | None = None,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        return self.calculator.calculate_from_system(
            obj, system, materials_by_id, losses_percent=losses_percent
        )

    def compare_systems(
        self,
        obj: ObjectData,
        systems: Sequence[tuple[str, Sequence[LayerInput]]],
    ) -> ComparisonResult:
        return self.comparison.compare(obj, systems)

    def format_summary(self, result: SystemCalculationResult) -> str:
        """Краткая текстовая сводка расчёта."""
        lines = [
            f"Система: {result.system.system_name}",
            f"Объект: {result.object_data.object_name or '—'}",
            f"Площадь: {result.object_data.area_m2 or '—'} м²",
            f"Общая толщина: {result.total_dft} мкм",
            f"Расход: {result.total_practical_consumption_kg} кг/м² "
            f"({result.total_practical_consumption_l} л/м²)",
            f"Стоимость: {result.total_cost_per_m2} руб/м²",
            f"Стоимость объекта: {result.total_cost} руб",
            "",
            "Слои:",
        ]
        for i, lr in enumerate(result.layers, 1):
            lines.append(
                f"  {i}. {lr.material.material_name}: "
                f"DFT={lr.target_dft} мкм, "
                f"{lr.practical_consumption_kg} кг/м², "
                f"{lr.cost_per_m2} руб/м²"
            )
        return "\n".join(lines)
