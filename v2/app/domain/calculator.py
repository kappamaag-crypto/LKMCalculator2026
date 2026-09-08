"""
Calculation engine — расчёт слоёв и систем.

Использует формулы из domain.formulas (1:1 со старым калькулятором).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Callable

from app.domain.models import (
    Material,
    LayerResult,
    CoatingSystem,
    LayerDefinition,
    ObjectData,
    SystemCalculationResult,
)
from app.domain.formulas import (
    LayerCalcInput,
    calculate_layer,
    scale_to_area,
    calculate_packages,
    total_area,
    round3,
)
from app.domain.validation import (
    ValidationResult,
    validate_before_calculation,
    validate_object_data,
)


@dataclass
class LayerInput:
    material: Material
    target_dft: float
    losses_percent: float = 0.0
    thinner_percent: float = 0.0
    thinner: Optional[Material] = None


class LayerCalculator:
    @staticmethod
    def calculate(
        material: Material,
        target_dft: float,
        losses_percent: float = 0.0,
        thinner_percent: float = 0.0,
        thinner: Optional[Material] = None,
        area_m2: float = 1.0,
    ) -> LayerResult:
        price_kg = material.price_per_kg or 0.0
        thinner_density = 1.0
        thinner_price = 0.0
        if thinner is not None:
            thinner_density = thinner.density if thinner.density > 0 else 1.0
            thinner_price = thinner.price_per_kg or 0.0
        elif material.thinner_name and thinner_percent > 0:
            thinner_density = 0.9

        inp = LayerCalcInput(
            density=material.density or 0.0,
            solids_percent=material.solids_percent or 0.0,
            dry_thickness=target_dft,
            losses_percent=losses_percent,
            price_per_kg=price_kg,
            thinner_percent=thinner_percent,
            thinner_density=thinner_density,
            thinner_price_per_kg=thinner_price,
        )
        calc = calculate_layer(inp)

        result = LayerResult(
            material=material,
            target_dft=target_dft,
            losses_percent=losses_percent,
            thinner_percent=thinner_percent,
            thinner=thinner,
            wft=calc.wft,
            theoretical_coverage=calc.theoretical_coverage,
            practical_coverage=calc.practical_coverage,
            theoretical_consumption_l=calc.theoretical_consumption_l,
            practical_consumption_l=calc.practical_consumption_l,
            theoretical_consumption_kg=calc.theoretical_consumption_kg,
            practical_consumption_kg=calc.practical_consumption_kg,
            cost_per_m2=calc.cost_per_m2,
            thinner_consumption_l=calc.thinner_consumption_l,
            thinner_consumption_kg=calc.thinner_consumption_kg,
            thinner_cost_per_m2=calc.thinner_cost_per_m2,
        )

        if area_m2 > 0:
            result.total_consumption_kg = scale_to_area(result.practical_consumption_kg, area_m2)
            result.total_consumption_l = scale_to_area(result.practical_consumption_l, area_m2)
            result.total_cost = scale_to_area(
                result.cost_per_m2 + result.thinner_cost_per_m2, area_m2
            )
            packaging = material.packaging_kg
            if packaging and packaging > 0:
                packages, purchase, remainder = calculate_packages(
                    result.total_consumption_kg, packaging
                )
                result.packages_count = packages
                result.purchase_kg = purchase
                result.remainder_kg = remainder
            else:
                result.packages_count = 0
                result.purchase_kg = result.total_consumption_kg
                result.remainder_kg = 0.0
        return result


class SystemCalculator:
    def __init__(
        self,
        compatibility_checker: Optional[Callable[[str, str], str]] = None,
        default_losses: float = 0.0,
    ):
        self.compatibility_checker = compatibility_checker
        self.default_losses = default_losses

    def resolve_area(self, obj: ObjectData) -> float:
        if obj.area_m2 > 0:
            return obj.area_m2
        if obj.area_per_element > 0 and obj.elements_count > 0:
            return total_area(obj.area_per_element, obj.elements_count)
        return 0.0

    def calculate(
        self,
        obj: ObjectData,
        layer_inputs: Sequence[LayerInput],
        system: Optional[CoatingSystem] = None,
        skip_validation: bool = False,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        validation = ValidationResult()
        if not skip_validation:
            layers_for_val = [
                (li.material, li.target_dft, li.losses_percent, li.thinner_percent)
                for li in layer_inputs
            ]
            validation = validate_before_calculation(
                obj, layers_for_val, self.compatibility_checker
            )
            if validation.has_errors:
                empty = SystemCalculationResult(
                    system=system or CoatingSystem(system_name="Ошибка валидации"),
                    object_data=obj,
                    calculated_at=datetime.now(),
                )
                return empty, validation

        area = self.resolve_area(obj)
        layer_results: list[LayerResult] = []

        for li in layer_inputs:
            losses = li.losses_percent if li.losses_percent is not None else self.default_losses
            lr = LayerCalculator.calculate(
                material=li.material,
                target_dft=li.target_dft,
                losses_percent=losses,
                thinner_percent=li.thinner_percent,
                thinner=li.thinner,
                area_m2=area,
            )
            layer_results.append(lr)

        total_dft = round3(sum(lr.target_dft for lr in layer_results))
        total_theor_kg = round3(sum(lr.theoretical_consumption_kg for lr in layer_results))
        total_pract_kg = round3(sum(lr.practical_consumption_kg for lr in layer_results))
        total_theor_l = round3(sum(lr.theoretical_consumption_l for lr in layer_results))
        total_pract_l = round3(sum(lr.practical_consumption_l for lr in layer_results))
        total_cost_m2 = round3(
            sum(lr.cost_per_m2 + lr.thinner_cost_per_m2 for lr in layer_results)
        )
        total_cost = round3(sum(lr.total_cost for lr in layer_results))
        total_thinner_cost = round3(
            sum(scale_to_area(lr.thinner_cost_per_m2, area) for lr in layer_results)
        )
        total_purchase = round3(
            sum(lr.purchase_kg * (lr.material.price_per_kg or 0) for lr in layer_results)
        )

        result = SystemCalculationResult(
            system=system or CoatingSystem(system_name="Пользовательская система"),
            object_data=obj,
            layers=layer_results,
            total_dft=total_dft,
            total_theoretical_consumption_kg=total_theor_kg,
            total_practical_consumption_kg=total_pract_kg,
            total_theoretical_consumption_l=total_theor_l,
            total_practical_consumption_l=total_pract_l,
            total_cost_per_m2=total_cost_m2,
            total_cost=total_cost,
            total_thinner_cost=total_thinner_cost,
            total_purchase_cost=total_purchase,
            calculated_at=datetime.now(),
        )
        return result, validation

    def calculate_from_system(
        self,
        obj: ObjectData,
        system: CoatingSystem,
        materials_by_id: dict[int, Material],
        losses_percent: float | None = None,
        skip_validation: bool = False,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        layer_inputs: list[LayerInput] = []
        losses = losses_percent if losses_percent is not None else self.default_losses

        for ld in system.layers:
            material = ld.material
            if material is None and ld.material_id is not None:
                material = materials_by_id.get(ld.material_id)
            if material is None:
                continue
            thinner = None
            if ld.thinner_material_id:
                thinner = materials_by_id.get(ld.thinner_material_id)
            layer_inputs.append(
                LayerInput(
                    material=material,
                    target_dft=ld.target_dft,
                    losses_percent=losses,
                    thinner_percent=ld.thinner_percent,
                    thinner=thinner,
                )
            )
        return self.calculate(obj, layer_inputs, system=system, skip_validation=skip_validation)
