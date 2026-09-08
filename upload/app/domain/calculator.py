"""
Calculation engine — расчёт слоёв и систем.

Все инженерные промежуточные значения сохраняются без округления.
Закупка, упаковки и остатки не рассчитываются.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Callable

from app.domain.models import Material, LayerResult, CoatingSystem, ObjectData, SystemCalculationResult
from app.domain.formulas import LayerCalcInput, calculate_layer, scale_to_area, total_area
from app.domain.validation import ValidationResult, validate_before_calculation


@dataclass
class LayerInput:
    material: Material
    target_dft: float
    losses_percent: float = 0.0
    thinner_percent: float = 0.0
    thinner: Optional[Material] = None
    thinner_basis: Optional[str] = None


class LayerCalculator:
    """Расчёт одного слоя без закупочной/складской логики."""

    @staticmethod
    def calculate(
        material: Material,
        target_dft: float,
        losses_percent: float = 0.0,
        thinner_percent: float = 0.0,
        thinner: Optional[Material] = None,
        area_m2: float = 1.0,
        thinner_basis: Optional[str] = None,
    ) -> LayerResult:
        if material.density is None or material.density <= 0:
            raise ValueError(f"Плотность материала «{material.material_name}» неизвестна или некорректна.")

        solids = material.solids_by_volume_percent
        if solids is None:
            solids = material.solids_percent
        if solids is None or solids <= 0:
            raise ValueError(f"Сухой остаток материала «{material.material_name}» неизвестен или некорректен.")

        # Стоимость нельзя считать при неизвестной цене: UNKNOWN не равен 0.
        if material.price_per_kg is None or material.price_per_kg < 0:
            raise ValueError(f"Цена материала «{material.material_name}» за кг неизвестна или некорректна.")
        price_kg = material.price_per_kg

        thinner_density: Optional[float] = None
        thinner_price: Optional[float] = None
        if thinner_percent > 0:
            if thinner is None:
                raise ValueError(
                    f"Для материала «{material.material_name}» задан разбавитель {thinner_percent}%, "
                    "но материал-разбавитель не загружен."
                )
            if thinner.density is None or thinner.density <= 0:
                raise ValueError(f"Плотность разбавителя «{thinner.material_name}» неизвестна или некорректна.")
            if thinner.price_per_kg is None or thinner.price_per_kg < 0:
                raise ValueError(f"Цена разбавителя «{thinner.material_name}» за кг неизвестна или некорректна.")
            thinner_density = thinner.density
            thinner_price = thinner.price_per_kg

        basis = thinner_basis or material.thinner_basis
        inp = LayerCalcInput(
            density=material.density,
            solids_percent=solids,
            dry_thickness=target_dft,
            losses_percent=losses_percent,
            price_per_kg=price_kg,
            thinner_percent=thinner_percent,
            thinner_density=thinner_density,
            thinner_price_per_kg=thinner_price,
            thinner_basis=basis,
        )
        calc = calculate_layer(inp)

        result = LayerResult(
            material=material,
            target_dft=target_dft,
            losses_percent=losses_percent,
            thinner_percent=thinner_percent,
            thinner=thinner,
            thinner_basis=basis,
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
            result.total_cost = scale_to_area(result.cost_per_m2 + result.thinner_cost_per_m2, area_m2)

        return result


class SystemCalculator:
    """Расчёт всей системы покрытия."""

    def __init__(self, compatibility_checker: Optional[Callable[[str, str], str]] = None, default_losses: float = 0.0):
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
            layers_for_val = [(li.material, li.target_dft, li.losses_percent, li.thinner_percent) for li in layer_inputs]
            validation = validate_before_calculation(obj, layers_for_val, self.compatibility_checker, system=system)
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
            layer_results.append(
                LayerCalculator.calculate(
                    material=li.material,
                    target_dft=li.target_dft,
                    losses_percent=losses,
                    thinner_percent=li.thinner_percent,
                    thinner=li.thinner,
                    area_m2=area,
                    thinner_basis=li.thinner_basis,
                )
            )

        total_dft = sum(lr.target_dft for lr in layer_results)
        total_theor_kg = sum(lr.theoretical_consumption_kg for lr in layer_results)
        total_pract_kg = sum(lr.practical_consumption_kg for lr in layer_results)
        total_theor_l = sum(lr.theoretical_consumption_l for lr in layer_results)
        total_pract_l = sum(lr.practical_consumption_l for lr in layer_results)
        total_cost_m2 = sum(lr.cost_per_m2 + lr.thinner_cost_per_m2 for lr in layer_results)
        total_cost = sum(lr.total_cost for lr in layer_results)
        total_thinner_cost = sum(scale_to_area(lr.thinner_cost_per_m2, area) for lr in layer_results)

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
            thinner = materials_by_id.get(ld.thinner_material_id) if ld.thinner_material_id else None
            layer_inputs.append(
                LayerInput(
                    material=material,
                    target_dft=ld.target_dft,
                    losses_percent=ld.losses_percent if ld.losses_percent is not None else losses,
                    thinner_percent=ld.thinner_percent,
                    thinner=thinner,
                    thinner_basis=ld.thinner_basis or material.thinner_basis,
                )
            )
        return self.calculate(obj, layer_inputs, system=system, skip_validation=skip_validation)
