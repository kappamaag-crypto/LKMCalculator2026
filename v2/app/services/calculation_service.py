"""Application service: расчёты и сравнение."""

from __future__ import annotations

from typing import Optional, Sequence

from app.domain.models import (
    ObjectData,
    SystemCalculationResult,
    ComparisonResult,
    CoatingSystem,
    Material,
)
from app.domain.calculator import SystemCalculator, LayerInput, LayerCalculator
from app.domain.comparison import ComparisonEngine
from app.domain.validation import ValidationResult


class CalculationService:
    def __init__(
        self,
        calculator: Optional[SystemCalculator] = None,
        comparison_engine: Optional[ComparisonEngine] = None,
    ):
        self.calculator = calculator or SystemCalculator()
        self.comparison = comparison_engine or ComparisonEngine(self.calculator)

    def calculate_system(
        self,
        obj: ObjectData,
        layers: Sequence[LayerInput],
        system: Optional[CoatingSystem] = None,
        skip_validation: bool = False,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        return self.calculator.calculate(
            obj, layers, system=system, skip_validation=skip_validation
        )

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
        lines = [
            f"Система: {result.system.system_name or 'Пользовательская'}",
            f"Слоёв: {len(result.layers)}",
            f"DFT: {result.total_dft:.0f} мкм",
            f"Расход: {result.total_practical_consumption_kg:.3f} кг/м²",
            f"Стоимость: {result.total_cost_per_m2:.2f} руб/м²",
            f"Объект: {result.total_cost:,.2f} руб".replace(",", " "),
        ]
        for i, lr in enumerate(result.layers, 1):
            lines.append(
                f"  {i}. {lr.material.material_name}: "
                f"DFT={lr.target_dft:.0f}, WFT={lr.wft:.1f}, "
                f"{lr.practical_consumption_kg:.3f} кг/м², "
                f"{lr.cost_per_m2:.2f} руб/м²"
            )
        return "\n".join(lines)
