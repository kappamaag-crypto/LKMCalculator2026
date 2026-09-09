"""Calculation engine — расчёт слоёв и систем.

Все инженерные промежуточные значения сохраняются без округления.
Закупка, упаковки и остатки не рассчитываются.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Callable
from app.domain.models import Material, LayerResult, CoatingSystem, ObjectData, SystemCalculationResult
from app.domain.formulas import LayerCalcInput, calculate_layer, scale_to_area
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
    @staticmethod
    def calculate(material: Material, target_dft: float, losses_percent: float = 0.0, thinner_percent: float = 0.0, thinner: Optional[Material] = None, area_m2: float = 1.0, thinner_basis: Optional[str] = None) -> LayerResult:
        if material.density is None or material.density <= 0:
            raise ValueError(f"Плотность материала «{material.material_name}» неизвестна или некорректна.")
        solids = material.solids_by_volume_percent
        if solids is None or solids <= 0 or solids > 100:
            raise ValueError(f"Объёмный сухой остаток материала «{material.material_name}» неизвестен или некорректен. Для расчёта DFT/WFT требуется solids_by_volume_percent в диапазоне 0–100 %.")
        if area_m2 < 0:
            raise ValueError("Площадь объекта не может быть отрицательной.")
        thinner_density, thinner_price = 1.0, None
        if thinner_percent > 0:
            if thinner is None:
                raise ValueError(f"Для материала «{material.material_name}» задан разбавитель {thinner_percent}%, но материал-разбавитель не загружен.")
            if thinner.density is None or thinner.density <= 0:
                raise ValueError(f"Плотность разбавителя «{thinner.material_name}» неизвестна или некорректна.")
            thinner_density, thinner_price = thinner.density, thinner.price_per_kg
        basis = thinner_basis or material.thinner_basis
        calc = calculate_layer(LayerCalcInput(density=material.density, solids_by_volume_percent=solids, dry_thickness=target_dft, losses_percent=losses_percent, price_per_kg=material.price_per_kg, price_per_liter=material.price_per_liter, thinner_percent=thinner_percent, thinner_density=thinner_density, thinner_price_per_kg=thinner_price, thinner_basis=basis))
        result = LayerResult(material=material,target_dft=target_dft,losses_percent=losses_percent,thinner_percent=thinner_percent,thinner=thinner,thinner_basis=basis,wft=calc.wft,theoretical_coverage=calc.theoretical_coverage,practical_coverage=calc.practical_coverage,theoretical_consumption_l=calc.theoretical_consumption_l,practical_consumption_l=calc.practical_consumption_l,theoretical_consumption_kg=calc.theoretical_consumption_kg,practical_consumption_kg=calc.practical_consumption_kg,cost_per_m2=calc.cost_per_m2,thinner_consumption_l=calc.thinner_consumption_l,thinner_consumption_kg=calc.thinner_consumption_kg,thinner_cost_per_m2=calc.thinner_cost_per_m2)
        if area_m2 > 0:
            result.total_consumption_kg = scale_to_area(result.practical_consumption_kg, area_m2)
            result.total_consumption_l = scale_to_area(result.practical_consumption_l, area_m2)
            result.total_cost = scale_to_area(result.cost_per_m2 + result.thinner_cost_per_m2, area_m2) if result.cost_per_m2 is not None and result.thinner_cost_per_m2 is not None else None
        return result

class SystemCalculator:
    def __init__(self, compatibility_checker: Optional[Callable[[str, str], str]] = None, default_losses: float = 0.0):
        self.compatibility_checker, self.default_losses = compatibility_checker, default_losses

    @staticmethod
    def resolve_area(obj: ObjectData) -> float:
        return obj.area_m2 if obj.area_m2 > 0 else 0.0

    def calculate(self, obj: ObjectData, layer_inputs: Sequence[LayerInput], system: Optional[CoatingSystem] = None, skip_validation: bool = False) -> tuple[SystemCalculationResult, ValidationResult]:
        validation = ValidationResult()
        if not skip_validation:
            layers_for_val = [(li.material, li.target_dft, li.losses_percent, li.thinner_percent) for li in layer_inputs]
            validation = validate_before_calculation(obj, layers_for_val, self.compatibility_checker, system=system)
            if validation.has_errors:
                return SystemCalculationResult(system=system or CoatingSystem(system_name="Ошибка валидации"), object_data=obj, calculated_at=datetime.now()), validation
        area = self.resolve_area(obj)
        if area <= 0:
            validation.add_error("OBJ_AREA_REQUIRED", "Для расчёта системы укажите площадь объекта больше нуля (например, 1 м² для расчёта на единицу площади).", "area_m2")
            return SystemCalculationResult(system=system or CoatingSystem(system_name="Ошибка валидации"), object_data=obj, calculated_at=datetime.now()), validation
        layer_results = [LayerCalculator.calculate(li.material, li.target_dft, li.losses_percent if li.losses_percent is not None else self.default_losses, li.thinner_percent, li.thinner, area, li.thinner_basis) for li in layer_inputs]
        total_dft = sum(lr.target_dft for lr in layer_results)
        total_theor_kg = sum(lr.theoretical_consumption_kg for lr in layer_results)
        total_pract_kg = sum(lr.practical_consumption_kg for lr in layer_results)
        total_theor_l = sum(lr.theoretical_consumption_l for lr in layer_results)
        total_pract_l = sum(lr.practical_consumption_l for lr in layer_results)
        all_layer_costs_known = all(lr.cost_per_m2 is not None and lr.thinner_cost_per_m2 is not None for lr in layer_results)
        total_cost_m2 = sum(lr.cost_per_m2 + lr.thinner_cost_per_m2 for lr in layer_results) if all_layer_costs_known else None
        all_total_costs_known = all(lr.total_cost is not None for lr in layer_results)
        total_cost = sum(lr.total_cost for lr in layer_results) if all_total_costs_known else None
        all_thinner_costs_known = all(lr.thinner_cost_per_m2 is not None for lr in layer_results)
        total_thinner_cost = sum(scale_to_area(lr.thinner_cost_per_m2, area) for lr in layer_results) if all_thinner_costs_known else None
        return SystemCalculationResult(system=system or CoatingSystem(system_name="Пользовательская система"),object_data=obj,layers=layer_results,total_dft=total_dft,total_theoretical_consumption_kg=total_theor_kg,total_practical_consumption_kg=total_pract_kg,total_theoretical_consumption_l=total_theor_l,total_practical_consumption_l=total_pract_l,total_cost_per_m2=total_cost_m2,total_cost=total_cost,total_thinner_cost=total_thinner_cost,calculated_at=datetime.now()), validation

    def calculate_from_system(self, obj: ObjectData, system: CoatingSystem, materials_by_id: dict[int, Material], losses_percent: float | None = None, skip_validation: bool = False) -> tuple[SystemCalculationResult, ValidationResult]:
        layer_inputs=[]
        losses=losses_percent if losses_percent is not None else self.default_losses
        missing=[]
        for ld in system.layers:
            material=ld.material
            if material is None and ld.material_id is not None: material=materials_by_id.get(ld.material_id)
            if material is None:
                missing.append(ld.layer_number)
                continue
            thinner=materials_by_id.get(ld.thinner_material_id) if ld.thinner_material_id else None
            layer_inputs.append(LayerInput(material=material,target_dft=ld.target_dft,losses_percent=losses,thinner_percent=ld.thinner_percent,thinner=thinner,thinner_basis=ld.thinner_basis))
        if missing:
            validation=ValidationResult()
            validation.add_error("SYSTEM_LAYER_MATERIAL_MISSING", f"Не загружен материал для слоя(ёв): {', '.join(map(str, missing))}.", "layers")
            return SystemCalculationResult(system=system,object_data=obj,calculated_at=datetime.now()), validation
        if not layer_inputs:
            validation=ValidationResult()
            validation.add_error("SYSTEM_NO_LAYERS", "Система не содержит доступных слоёв для расчёта.", "layers")
            return SystemCalculationResult(system=system,object_data=obj,calculated_at=datetime.now()), validation
        return self.calculate(obj, layer_inputs, system=system, skip_validation=skip_validation)
