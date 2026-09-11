"""Application service for evaluating scenario alternatives.

All arithmetic is delegated to CalculationService. This layer only validates
and orchestrates alternatives so Excel/PDF and comparison keep using the same
calculation result model.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.calculation_scenario import CalculationScenario
from app.domain.models import SystemCalculationResult
from app.services.calculation_service import CalculationService


@dataclass(frozen=True)
class ScenarioAlternativeResult:
    system_name: str
    result: SystemCalculationResult


@dataclass(frozen=True)
class CalculationScenarioResult:
    scenario_name: str
    alternatives: tuple[ScenarioAlternativeResult, ...]


class CalculationScenarioService:
    def __init__(self, calculation_service: CalculationService | None = None):
        self.calculation_service = calculation_service or CalculationService()

    def evaluate(self, scenario: CalculationScenario) -> CalculationScenarioResult:
        scenario.validate()
        evaluated: list[ScenarioAlternativeResult] = []
        for system in scenario.alternatives:
            materials_by_id = {
                layer.material_id: layer.material
                for layer in system.layers
                if layer.material_id is not None and layer.material is not None
            }
            if len(materials_by_id) != len(
                [layer for layer in system.layers if layer.material_id is not None]
            ):
                raise ValueError(
                    f"Система «{system.system_name}» содержит слой без Material"
                )
            result, validation = self.calculation_service.calculate_from_template(
                scenario.object_data,
                system,
                materials_by_id,
                engineering_context=scenario.engineering_context,
            )
            if validation.has_errors:
                messages = "; ".join(error.message for error in validation.errors)
                raise ValueError(
                    f"Система «{system.system_name}» не прошла валидацию: {messages}"
                )
            evaluated.append(
                ScenarioAlternativeResult(system_name=system.system_name, result=result)
            )
        return CalculationScenarioResult(
            scenario_name=scenario.name,
            alternatives=tuple(evaluated),
        )
