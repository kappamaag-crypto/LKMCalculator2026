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
            layers_with_material_ids = [
                layer for layer in system.layers if layer.material_id is not None
            ]
            materials_by_id = {
                layer.material_id: layer.material
                for layer in layers_with_material_ids
                if layer.material is not None
            }
            missing_materials = [
                layer.layer_number
                for layer in layers_with_material_ids
                if layer.material is None
            ]
            if missing_materials:
                raise ValueError(
                    f"Система «{system.system_name}» содержит слой(и) без Material: "
                    + ", ".join(str(number) for number in missing_materials)
                )
            if any(layer.material_id is None for layer in system.layers):
                raise ValueError(
                    f"Система «{system.system_name}» содержит слой без material_id"
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
