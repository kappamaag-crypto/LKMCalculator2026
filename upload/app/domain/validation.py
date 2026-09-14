"""Валидация входных данных и результатов расчёта."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence
from app.domain.models import Material, LayerDefinition, LayerResult, CoatingSystem, ObjectData
from app.domain.formulas import DILUTION_BASIS_BY_PAINT_VOLUME, DILUTION_BASIS_BY_MIX_VOLUME, DILUTION_BASIS_BY_MASS, DILUTION_BASIS_BY_COMPONENT_VOLUME

VALID_THINNER_BASES = {DILUTION_BASIS_BY_PAINT_VOLUME, DILUTION_BASIS_BY_MIX_VOLUME, DILUTION_BASIS_BY_MASS, DILUTION_BASIS_BY_COMPONENT_VOLUME}

@dataclass
class ValidationIssue:
    level: str
    code: str
    message: str
    field: Optional[str] = None
    layer_index: Optional[int] = None

@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)
    @property
    def has_errors(self): return any(i.level == "error" for i in self.issues)
    @property
    def has_warnings(self): return any(i.level == "warning" for i in self.issues)
    @property
    def errors(self): return [i for i in self.issues if i.level == "error"]
    @property
    def warnings(self): return [i for i in self.issues if i.level == "warning"]
    def add_error(self, code, message, field=None, layer_index=None): self.issues.append(ValidationIssue("error", code, message, field, layer_index))
    def add_warning(self, code, message, field=None, layer_index=None): self.issues.append(ValidationIssue("warning", code, message, field, layer_index))
    def add_info(self, code, message, field=None, layer_index=None): self.issues.append(ValidationIssue("info", code, message, field, layer_index))
    def merge(self, other): self.issues.extend(other.issues)

def _range(result, minimum, maximum, code, message, field):
    if minimum is not None and maximum is not None and minimum > maximum: result.add_error(code, message, field)

def _is_thinner(material: Material) -> bool:
    return getattr(getattr(material, "material_type", None), "value", "") == "разбавитель"

def validate_material(material: Material) -> ValidationResult:
    r = ValidationResult()
    if not material.material_name or not material.material_name.strip(): r.add_error("MAT_NAME", "Не указано название материала", "material_name")
    if material.density is None: r.add_error("MAT_DENSITY_UNKNOWN", "Плотность материала неизвестна — расчёт массы в кг невозможен", "density")
    elif material.density <= 0: r.add_error("MAT_DENSITY_INVALID", "Плотность материала должна быть больше нуля", "density")
    if material.solids_by_volume_percent is None:
        if not _is_thinner(material): r.add_error("MAT_SOLIDS_UNKNOWN", "Объёмная доля сухого остатка неизвестна — инженерный расчёт WFT невозможен", "solids_by_volume_percent")
    else:
        sv = material.solids_by_volume_percent
        if sv < 0: r.add_error("MAT_SV_LT0", "Сухой остаток по объёму не может быть отрицательным", "solids_by_volume_percent")
        elif sv > 100: r.add_error("MAT_SV_GT100", "Сухой остаток по объёму не может превышать 100 %", "solids_by_volume_percent")
        elif sv == 0 and not _is_thinner(material): r.add_error("MAT_SV_ZERO", "Сухой остаток по объёму равен 0 % — расчёт WFT невозможен", "solids_by_volume_percent")
    if material.solids_percent is not None:
        if material.solids_percent < 0: r.add_error("MAT_SOLIDS_LT0", "Сухой остаток не может быть отрицательным", "solids_percent")
        elif material.solids_percent > 100: r.add_error("MAT_SOLIDS_GT100", "Сухой остаток не может превышать 100 %", "solids_percent")
    if material.price_per_kg is not None and material.price_per_kg < 0: r.add_error("MAT_PRICE_NEG", "Цена не может быть отрицательной", "price_per_kg")
    if material.price_per_liter is not None and material.price_per_liter < 0: r.add_error("MAT_PRICE_L_NEG", "Цена за литр не может быть отрицательной", "price_per_liter")
    _range(r, material.min_application_temperature, material.max_application_temperature, "MAT_TEMP_RANGE", "Диапазон температуры нанесения задан некорректно", "application_temperature")
    _range(r, material.min_recoat_time_h, material.max_recoat_time_h, "MAT_RECOAT_RANGE", "Диапазон межслойной выдержки задан некорректно", "recoat_time_h")
    if material.max_relative_humidity is not None and not 0 <= material.max_relative_humidity <= 100: r.add_error("MAT_RH_MAX_RANGE", "Максимальная относительная влажность должна быть в диапазоне 0–100 %", "max_relative_humidity")
    if material.min_dew_point_margin_c is not None and material.min_dew_point_margin_c < 0: r.add_error("MAT_DEW_MARGIN_NEG", "Минимальный запас до точки росы не может быть отрицательным", "min_dew_point_margin_c")
    if material.recommended_dft_min is not None and material.recommended_dft_min < 0: r.add_error("MAT_DFT_MIN_NEG", "Минимальная рекомендуемая толщина не может быть отрицательной", "recommended_dft_min")
    if material.recommended_dft_max is not None and material.recommended_dft_max < 0: r.add_error("MAT_DFT_MAX_NEG", "Максимальная рекомендуемая толщина не может быть отрицательной", "recommended_dft_max")
    if material.max_single_layer_dft is not None and material.max_single_layer_dft <= 0: r.add_error("MAT_DFT_SINGLE_INVALID", "Максимальная толщина одного слоя должна быть больше нуля", "max_single_layer_dft")
    if material.recommended_dft_min is not None and material.recommended_dft_max is not None and material.recommended_dft_min > material.recommended_dft_max: r.add_error("MAT_DFT_RANGE", "Минимальная рекомендуемая толщина больше максимальной", "recommended_dft")
    if material.thinner_percent_min is not None and material.thinner_percent_min < 0: r.add_error("MAT_THINNER_MIN_NEG", "Минимальный процент разбавителя не может быть отрицательным", "thinner_percent_min")
    if material.thinner_percent_max is not None and material.thinner_percent_max < 0: r.add_error("MAT_THINNER_MAX_NEG", "Максимальный процент разбавителя не может быть отрицательным", "thinner_percent_max")
    if material.thinner_percent_min is not None and material.thinner_percent_max is not None and material.thinner_percent_min > material.thinner_percent_max: r.add_error("MAT_THINNER_RANGE", "Минимальный процент разбавителя больше максимального", "thinner_percent")
    if material.thinner_basis is not None and material.thinner_basis not in VALID_THINNER_BASES: r.add_error("MAT_THINNER_BASIS", f"Неизвестная база расчёта разбавления: «{material.thinner_basis}»", "thinner_basis")
    return r

def validate_layer_input(material: Material, target_dft: float | None, losses_percent: float | None = 0.0, thinner_percent: float | None = 0.0, layer_index: int | None = None, thinner_basis: str | None = None) -> ValidationResult:
    r = ValidationResult(); mr = validate_material(material); r.merge(mr)
    for issue in r.issues: issue.layer_index = layer_index
    if target_dft is None: r.add_error("LAYER_DFT_UNKNOWN", "Не задана толщина сухого слоя (DFT) — укажите значение в мкм", "target_dft", layer_index)
    else:
        if target_dft < 0: r.add_error("LAYER_DFT_NEG", "Толщина сухого слоя не может быть отрицательной", "target_dft", layer_index)
        elif target_dft == 0: r.add_error("LAYER_DFT_ZERO", "Толщина сухого слоя равна нулю — расчёт слоя невозможен", "target_dft", layer_index)
    if losses_percent is None: r.add_error("LAYER_LOSSES_UNKNOWN", "Не задан процент технологических потерь — укажите значение", "losses_percent", layer_index)
    else:
        if losses_percent < 0: r.add_error("LAYER_LOSSES_NEG", "Потери не могут быть отрицательными", "losses_percent", layer_index)
        if losses_percent >= 100: r.add_error("LAYER_LOSSES_GE100", "Потери не могут быть ≥ 100 %", "losses_percent", layer_index)
    if thinner_percent is None: r.add_error("LAYER_THINNER_UNKNOWN", "Не задан процент разбавления — укажите значение или 0 %", "thinner_percent", layer_index)
    else:
        if thinner_percent < 0: r.add_error("LAYER_THINNER_NEG", "Процент разбавителя не может быть отрицательным", "thinner_percent", layer_index)
        if thinner_percent >= 100: r.add_error("LAYER_THINNER_GE100", "Процент разбавителя должен быть меньше 100 %", "thinner_percent", layer_index)
    basis = thinner_basis if thinner_basis is not None else material.thinner_basis
    if thinner_percent is not None and thinner_percent > 0:
        if basis not in VALID_THINNER_BASES: r.add_error("LAYER_THINNER_BASIS", f"Для активного разбавления нужно явно указать допустимую базу: «{basis}»", "thinner_basis", layer_index)
    if thinner_percent is not None:
        if material.thinner_required and thinner_percent <= 0: r.add_warning("LAYER_THINNER_REQUIRED", f"Для «{material.material_name}» указан обязательный разбавитель, но процент разбавления не задан", "thinner_percent", layer_index)
        if material.thinner_percent_min is not None and thinner_percent < material.thinner_percent_min: r.add_warning("LAYER_THINNER_BELOW_MIN", f"Разбавление {thinner_percent:g} % ниже рекомендованного минимума {material.thinner_percent_min:g} %", "thinner_percent", layer_index)
        if material.thinner_percent_max is not None and thinner_percent > material.thinner_percent_max: r.add_error("LAYER_THINNER_ABOVE_MAX", f"Разбавление {thinner_percent:g} % превышает допустимый максимум {material.thinner_percent_max:g} %", "thinner_percent", layer_index)
        if basis == DILUTION_BASIS_BY_MIX_VOLUME and thinner_percent >= 100: r.add_error("LAYER_MIX_DILUTION_INVALID", "При расчёте разбавления как доли конечной смеси процент должен быть меньше 100 %", "thinner_percent", layer_index)
    if target_dft is not None:
        if material.recommended_dft_min is not None and target_dft > 0 and target_dft < material.recommended_dft_min: r.add_warning("LAYER_DFT_BELOW_MIN", f"Толщина {target_dft} мкм ниже рекомендуемого минимума ({material.recommended_dft_min} мкм) для «{material.material_name}»", "target_dft", layer_index)
        if material.recommended_dft_max is not None and target_dft > 0 and target_dft > material.recommended_dft_max: r.add_warning("LAYER_DFT_ABOVE_MAX", f"Толщина {target_dft} мкм выше рекомендуемого максимума ({material.recommended_dft_max} мкм) для «{material.material_name}»", "target_dft", layer_index)
        if material.max_single_layer_dft is not None and target_dft > material.max_single_layer_dft: r.add_error("LAYER_DFT_MAX_SINGLE", f"Толщина {target_dft} мкм превышает максимальную толщину одного слоя ({material.max_single_layer_dft} мкм) для «{material.material_name}»", "target_dft", layer_index)
    return r

def validate_application_conditions(obj: ObjectData, material: Material, layer_index: int | None = None) -> ValidationResult:
    r = ValidationResult(); temperature = obj.surface_temperature if obj.surface_temperature is not None else obj.air_temperature
    if temperature is not None:
        if material.min_application_temperature is not None and temperature < material.min_application_temperature: r.add_error("COND_TEMP_BELOW_MIN", f"Температура {temperature:g} °C ниже минимальной для «{material.material_name}» ({material.min_application_temperature:g} °C)", "surface_temperature", layer_index)
        if material.max_application_temperature is not None and temperature > material.max_application_temperature: r.add_error("COND_TEMP_ABOVE_MAX", f"Температура {temperature:g} °C выше максимальной для «{material.material_name}» ({material.max_application_temperature:g} °C)", "surface_temperature", layer_index)
    if obj.relative_humidity is not None and material.max_relative_humidity is not None and obj.relative_humidity > material.max_relative_humidity: r.add_error("COND_RH_ABOVE_MAX", f"Относительная влажность {obj.relative_humidity:g} % превышает допустимую для «{material.material_name}» ({material.max_relative_humidity:g} %)", "relative_humidity", layer_index)
    if obj.surface_temperature is not None and obj.dew_point is not None:
        margin = obj.surface_temperature - obj.dew_point
        if material.min_dew_point_margin_c is None: r.add_warning("COND_DEW_MARGIN_UNKNOWN", f"Минимальный запас до точки росы для «{material.material_name}» не указан — автоматическая проверка запаса невозможна", "dew_point_margin_c", layer_index)
        elif margin < material.min_dew_point_margin_c: r.add_error("COND_DEW_MARGIN", f"Запас температуры поверхности до точки росы {margin:.1f} °C меньше требуемого {material.min_dew_point_margin_c:.1f} °C для «{material.material_name}»", "dew_point_margin_c", layer_index)
    return r

def validate_object_data(obj: ObjectData) -> ValidationResult:
    r = ValidationResult()
    if obj.area_m2 is None: r.add_error("OBJ_AREA_UNKNOWN", "Не задана площадь объекта — укажите площадь в м²", "area_m2")
    elif obj.area_m2 < 0: r.add_error("OBJ_AREA_NEG", "Площадь не может быть отрицательной", "area_m2")
    elif obj.area_m2 == 0: r.add_error("OBJ_AREA_ZERO", "Площадь должна быть больше нуля", "area_m2")
    if obj.temperature_min is not None and obj.temperature_max is not None and obj.temperature_min > obj.temperature_max: r.add_error("OBJ_TEMP_RANGE", "Минимальная температура объекта больше максимальной", "temperature_range")
    if obj.relative_humidity is not None and not 0 <= obj.relative_humidity <= 100: r.add_error("OBJ_RH_RANGE", "Относительная влажность должна быть в диапазоне 0–100 %", "relative_humidity")
    if obj.roughness is not None and obj.roughness < 0: r.add_error("OBJ_ROUGHNESS_NEG", "Шероховатость не может быть отрицательной", "roughness")
    if obj.surface_temperature is not None and obj.dew_point is not None and obj.surface_temperature < obj.dew_point: r.add_error("OBJ_DEW_POINT", "Температура поверхности ниже точки росы", "dew_point")
    if obj.dew_point_margin_c is not None and obj.dew_point_margin_c < 0: r.add_error("OBJ_DEW_MARGIN_NEG", "Запас до точки росы не может быть отрицательным", "dew_point_margin_c")
    return r

def validate_system_layers(layers: Sequence[LayerDefinition | LayerResult], compatibility_checker=None, system: CoatingSystem | None = None) -> ValidationResult:
    r = ValidationResult()
    if not layers:
        r.add_error("SYSTEM_NO_LAYERS", "Система не содержит слоёв", "layers")
        return r
    for idx, layer in enumerate(layers, 1):
        material = getattr(layer, "material", None)
        if material is None:
            r.add_error("SYSTEM_MATERIAL_UNKNOWN", f"Не задан материал для слоя №{idx}", "material", idx)
            continue
        target_dft = getattr(layer, "target_dft", None)
        losses = getattr(layer, "losses_percent", None)
        thinner = getattr(layer, "thinner_percent", None)
        r.merge(validate_layer_input(material, target_dft, losses, thinner, idx, getattr(layer, "thinner_basis", None)))
    if system is not None:
        expected_layers = system.number_of_layers
        if expected_layers > 0 and expected_layers != len(layers):
            r.add_error("SYS_LAYER_COUNT", f"В системе заявлено {expected_layers} слоёв, фактически задано {len(layers)}.", "number_of_layers")
        total_dft = sum((getattr(layer, "target_dft", None) or 0.0) for layer in layers)
        if system.total_dft_min is not None and total_dft < system.total_dft_min:
            r.add_error("SYS_TOTAL_DFT_BELOW_MIN", f"Общая DFT {total_dft:g} мкм ниже минимальной для системы ({system.total_dft_min:g} мкм).", "total_dft_min")
        if system.total_dft_max is not None and total_dft > system.total_dft_max:
            r.add_error("SYS_TOTAL_DFT_ABOVE_MAX", f"Общая DFT {total_dft:g} мкм выше максимальной для системы ({system.total_dft_max:g} мкм).", "total_dft_max")
    if compatibility_checker and len(layers) > 1:
        for prev, cur in zip(layers, layers[1:]):
            prev_name = getattr(getattr(prev, "material", None), "material_name", None); cur_name = getattr(getattr(cur, "material", None), "material_name", None)
            if not prev_name or not cur_name: continue
            try: message = compatibility_checker(prev_name, cur_name)
            except (TypeError, ValueError) as exc:
                r.add_warning("COMPATIBILITY_CHECK_ERROR", f"Проверка совместимости слоёв не выполнена: {exc}", "compatibility"); continue
            if message: r.add_error("LAYER_COMPATIBILITY", message, "compatibility")
    return r

def validate_before_calculation(obj: ObjectData, layers: Sequence[tuple[Material, float | None, float | None, float | None]], compatibility_checker=None, system=None) -> ValidationResult:
    r = validate_object_data(obj)
    for idx, (material, dft, losses, thinner) in enumerate(layers, 1): r.merge(validate_layer_input(material, dft, losses, thinner, idx))
    if system is not None: r.merge(validate_system_layers(system.layers, compatibility_checker, system))
    return r
