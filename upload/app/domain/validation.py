"""Валидация входных данных и результатов расчёта.

Все сообщения об ошибках — на русском языке.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import (
    Material,
    LayerDefinition,
    LayerResult,
    CoatingSystem,
    ObjectData,
    SystemCalculationResult,
)
from app.domain.enums import CompatibilityStatus
from app.domain.formulas import (
    DILUTION_BASIS_BY_PAINT_VOLUME,
    DILUTION_BASIS_BY_MIX_VOLUME,
    DILUTION_BASIS_BY_MASS,
    DILUTION_BASIS_BY_COMPONENT_VOLUME,
)


VALID_THINNER_BASES = {
    DILUTION_BASIS_BY_PAINT_VOLUME,
    DILUTION_BASIS_BY_MIX_VOLUME,
    DILUTION_BASIS_BY_MASS,
    DILUTION_BASIS_BY_COMPONENT_VOLUME,
}


@dataclass
class ValidationIssue:
    """Одна проблема валидации."""

    level: str          # "error" | "warning" | "info"
    code: str
    message: str
    field: Optional[str] = None
    layer_index: Optional[int] = None


@dataclass
class ValidationResult:
    """Результат проверки."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.level == "warning" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    def add_error(self, code: str, message: str, field: str | None = None, layer_index: int | None = None) -> None:
        self.issues.append(ValidationIssue("error", code, message, field, layer_index))

    def add_warning(self, code: str, message: str, field: str | None = None, layer_index: int | None = None) -> None:
        self.issues.append(ValidationIssue("warning", code, message, field, layer_index))

    def add_info(self, code: str, message: str, field: str | None = None, layer_index: int | None = None) -> None:
        self.issues.append(ValidationIssue("info", code, message, field, layer_index))

    def merge(self, other: "ValidationResult") -> None:
        self.issues.extend(other.issues)


def validate_material(material: Material) -> ValidationResult:
    """Проверка материала и его технических диапазонов."""
    result = ValidationResult()

    if not material.material_name or not material.material_name.strip():
        result.add_error("MAT_NAME", "Не указано название материала", "material_name")

    if material.density is not None and material.density < 0:
        result.add_error("MAT_DENSITY_NEG", "Плотность не может быть отрицательной", "density")
    if material.density == 0 and material.material_type.value != "разбавитель":
        result.add_warning("MAT_DENSITY_ZERO", "Плотность равна нулю — расчёт расхода будет невозможен", "density")

    if material.solids_percent is not None:
        if material.solids_percent < 0:
            result.add_error("MAT_SOLIDS_NEG", "Сухой остаток не может быть отрицательным", "solids_percent")
        if material.solids_percent > 100:
            result.add_error("MAT_SOLIDS_GT100", "Сухой остаток не может превышать 100 %", "solids_percent")
        if material.solids_percent == 0 and material.material_type.value != "разбавитель":
            result.add_warning("MAT_SOLIDS_ZERO", "Сухой остаток равен 0 % — расчёт толщины мокрой плёнки невозможен", "solids_percent")

    if material.solids_by_volume_percent is not None:
        if material.solids_by_volume_percent < 0:
            result.add_error("MAT_SV_NEG", "Сухой остаток по объёму не может быть отрицательным", "solids_by_volume_percent")
        if material.solids_by_volume_percent > 100:
            result.add_error("MAT_SV_GT100", "Сухой остаток по объёму не может превышать 100 %", "solids_by_volume_percent")
        if material.solids_by_volume_percent == 0 and material.material_type.value != "разбавитель":
            result.add_warning("MAT_SV_ZERO", "Сухой остаток по объёму равен 0 % — расчёт WFT невозможен", "solids_by_volume_percent")

    if material.price_per_kg is not None and material.price_per_kg < 0:
        result.add_error("MAT_PRICE_NEG", "Цена не может быть отрицательной", "price_per_kg")
    if material.price_per_liter is not None and material.price_per_liter < 0:
        result.add_error("MAT_PRICE_L_NEG", "Цена за литр не может быть отрицательной", "price_per_liter")

    _validate_ordered_range(
        result,
        material.min_application_temperature,
        material.max_application_temperature,
        "MAT_TEMP_RANGE",
        "Диапазон температуры нанесения задан некорректно",
        "application_temperature",
    )
    _validate_ordered_range(
        result,
        material.min_recoat_time_h,
        material.max_recoat_time_h,
        "MAT_RECOAT_RANGE",
        "Диапазон межслойной выдержки задан некорректно",
        "recoat_time_h",
    )

    if material.max_relative_humidity is not None and not 0 <= material.max_relative_humidity <= 100:
        result.add_error("MAT_RH_MAX_RANGE", "Максимальная относительная влажность должна быть в диапазоне 0–100 %", "max_relative_humidity")

    if material.min_dew_point_margin_c is not None and material.min_dew_point_margin_c < 0:
        result.add_error("MAT_DEW_MARGIN_NEG", "Минимальный запас до точки росы не может быть отрицательным", "min_dew_point_margin_c")

    if material.recommended_dft_min is not None and material.recommended_dft_min < 0:
        result.add_error("MAT_DFT_MIN_NEG", "Минимальная рекомендуемая толщина не может быть отрицательной", "recommended_dft_min")
    if material.recommended_dft_max is not None and material.recommended_dft_max < 0:
        result.add_error("MAT_DFT_MAX_NEG", "Максимальная рекомендуемая толщина не может быть отрицательной", "recommended_dft_max")
    if material.max_single_layer_dft is not None and material.max_single_layer_dft <= 0:
        result.add_error("MAT_DFT_SINGLE_INVALID", "Максимальная толщина одного слоя должна быть больше нуля", "max_single_layer_dft")

    if material.recommended_dft_min is not None and material.recommended_dft_max is not None:
        if material.recommended_dft_min > material.recommended_dft_max:
            result.add_error(
                "MAT_DFT_RANGE",
                f"Минимальная рекомендуемая толщина ({material.recommended_dft_min}) "
                f"больше максимальной ({material.recommended_dft_max})",
                "recommended_dft",
            )

    if material.thinner_percent_min is not None and material.thinner_percent_min < 0:
        result.add_error("MAT_THINNER_MIN_NEG", "Минимальный процент разбавителя не может быть отрицательным", "thinner_percent_min")
    if material.thinner_percent_max is not None and material.thinner_percent_max < 0:
        result.add_error("MAT_THINNER_MAX_NEG", "Максимальный процент разбавителя не может быть отрицательным", "thinner_percent_max")
    if (
        material.thinner_percent_min is not None
        and material.thinner_percent_max is not None
        and material.thinner_percent_min > material.thinner_percent_max
    ):
        result.add_error("MAT_THINNER_RANGE", "Минимальный процент разбавителя больше максимального", "thinner_percent")
    if material.thinner_basis not in VALID_THINNER_BASES:
        result.add_error(
            "MAT_THINNER_BASIS",
            f"Неизвестная база расчёта разбавления: «{material.thinner_basis}»",
            "thinner_basis",
        )

    return result


def _validate_ordered_range(
    result: ValidationResult,
    minimum: Optional[float],
    maximum: Optional[float],
    code: str,
    message: str,
    field: str,
) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        result.add_error(code, message, field)


def validate_layer_input(
    material: Material,
    target_dft: float,
    losses_percent: float = 0.0,
    thinner_percent: float = 0.0,
    layer_index: int | None = None,
    thinner_basis: str | None = None,
) -> ValidationResult:
    """Проверка входных данных слоя перед расчётом."""
    result = ValidationResult()

    mat_result = validate_material(material)
    for issue in mat_result.issues:
        issue.layer_index = layer_index
        result.issues.append(issue)

    if target_dft < 0:
        result.add_error("LAYER_DFT_NEG", "Толщина сухого слоя не может быть отрицательной", "target_dft", layer_index)
    if target_dft == 0:
        result.add_warning("LAYER_DFT_ZERO", "Толщина сухого слоя равна нулю", "target_dft", layer_index)

    if losses_percent < 0:
        result.add_error("LAYER_LOSSES_NEG", "Потери не могут быть отрицательными", "losses_percent", layer_index)
    if losses_percent >= 100:
        result.add_error("LAYER_LOSSES_GE100", "Потери не могут быть ≥ 100 %", "losses_percent", layer_index)

    if thinner_percent < 0:
        result.add_error("LAYER_THINNER_NEG", "Процент разбавителя не может быть отрицательным", "thinner_percent", layer_index)
    if thinner_percent > 100:
        result.add_error("LAYER_THINNER_GT100", "Процент разбавителя не может превышать 100 %", "thinner_percent", layer_index)

    basis = thinner_basis or material.thinner_basis
    if basis not in VALID_THINNER_BASES:
        result.add_error("LAYER_THINNER_BASIS", f"Неизвестная база разбавления: «{basis}»", "thinner_basis", layer_index)

    if material.thinner_required and thinner_percent <= 0:
        result.add_warning(
            "LAYER_THINNER_REQUIRED",
            f"Для «{material.material_name}» указан обязательный разбавитель, но процент разбавления не задан",
            "thinner_percent",
            layer_index,
        )

    if material.thinner_percent_min is not None and thinner_percent < material.thinner_percent_min:
        result.add_warning(
            "LAYER_THINNER_BELOW_MIN",
            f"Разбавление {thinner_percent:g} % ниже рекомендованного минимума {material.thinner_percent_min:g} %",
            "thinner_percent",
            layer_index,
        )
    if material.thinner_percent_max is not None and thinner_percent > material.thinner_percent_max:
        result.add_error(
            "LAYER_THINNER_ABOVE_MAX",
            f"Разбавление {thinner_percent:g} % превышает допустимый максимум {material.thinner_percent_max:g} %",
            "thinner_percent",
            layer_index,
        )

    if basis == DILUTION_BASIS_BY_MIX_VOLUME and thinner_percent >= 100:
        result.add_error("LAYER_MIX_DILUTION_INVALID", "При расчёте разбавления как доли конечной смеси процент должен быть меньше 100 %", "thinner_percent", layer_index)

    if material.recommended_dft_min is not None and target_dft > 0 and target_dft < material.recommended_dft_min:
        result.add_warning(
            "LAYER_DFT_BELOW_MIN",
            f"Толщина {target_dft} мкм ниже рекомендуемого минимума ({material.recommended_dft_min} мкм) для «{material.material_name}»",
            "target_dft",
            layer_index,
        )
    if material.recommended_dft_max is not None and target_dft > 0 and target_dft > material.recommended_dft_max:
        result.add_warning(
            "LAYER_DFT_ABOVE_MAX",
            f"Толщина {target_dft} мкм выше рекомендуемого максимума ({material.recommended_dft_max} мкм) для «{material.material_name}»",
            "target_dft",
            layer_index,
        )
    if material.max_single_layer_dft is not None and target_dft > material.max_single_layer_dft:
        result.add_error(
            "LAYER_DFT_MAX_SINGLE",
            f"Толщина {target_dft} мкм превышает максимальную толщину одного слоя ({material.max_single_layer_dft} мкм) для «{material.material_name}»",
            "target_dft",
            layer_index,
        )

    return result


def validate_application_conditions(
    obj: ObjectData,
    material: Material,
    layer_index: int | None = None,
) -> ValidationResult:
    """Проверка фактических условий нанесения относительно ТУ/ТДС материала."""
    result = ValidationResult()

    temperature = obj.surface_temperature
    if temperature is None:
        temperature = obj.air_temperature

    if temperature is not None:
        if material.min_application_temperature is not None and temperature < material.min_application_temperature:
            result.add_error(
                "COND_TEMP_BELOW_MIN",
                f"Температура {temperature:g} °C ниже минимальной для «{material.material_name}» ({material.min_application_temperature:g} °C)",
                "surface_temperature",
                layer_index,
            )
        if material.max_application_temperature is not None and temperature > material.max_application_temperature:
            result.add_error(
                "COND_TEMP_ABOVE_MAX",
                f"Температура {temperature:g} °C выше максимальной для «{material.material_name}» ({material.max_application_temperature:g} °C)",
                "surface_temperature",
                layer_index,
            )

    if obj.relative_humidity is not None and material.max_relative_humidity is not None:
        if obj.relative_humidity > material.max_relative_humidity:
            result.add_error(
                "COND_RH_ABOVE_MAX",
                f"Относительная влажность {obj.relative_humidity:g} % превышает допустимую для «{material.material_name}» ({material.max_relative_humidity:g} %)",
                "relative_humidity",
                layer_index,
            )

    if obj.surface_temperature is not None and obj.dew_point is not None:
        margin = obj.surface_temperature - obj.dew_point
        required = material.min_dew_point_margin_c if material.min_dew_point_margin_c is not None else 0.0
        if margin < required:
            result.add_error(
                "COND_DEW_MARGIN",
                f"Запас температуры поверхности до точки росы {margin:.1f} °C меньше требуемого {required:.1f} °C для «{material.material_name}»",
                "dew_point_margin_c",
                layer_index,
            )

    return result


def validate_object_data(obj: ObjectData) -> ValidationResult:
    """Проверка исходных данных объекта."""
    result = ValidationResult()

    if obj.area_m2 < 0:
        result.add_error("OBJ_AREA_NEG", "Площадь не может быть отрицательной", "area_m2")
    if obj.area_m2 == 0 and obj.area_per_element <= 0:
        result.add_warning("OBJ_AREA_ZERO", "Площадь равна нулю — итоговые количества будут нулевыми", "area_m2")

    if obj.elements_count < 0:
        result.add_error("OBJ_ELEMENTS_NEG", "Количество элементов не может быть отрицательным", "elements_count")

    if obj.area_per_element < 0:
        result.add_error("OBJ_AREA_PER_EL_NEG", "Площадь элемента не может быть отрицательной", "area_per_element")

    if obj.temperature_min is not None and obj.temperature_max is not None and obj.temperature_min > obj.temperature_max:
        result.add_error("OBJ_TEMP_RANGE", "Минимальная температура объекта больше максимальной", "temperature_range")

    if obj.relative_humidity is not None:
        if obj.relative_humidity < 0 or obj.relative_humidity > 100:
            result.add_error("OBJ_RH_RANGE", "Относительная влажность должна быть в диапазоне 0–100 %", "relative_humidity")

    if obj.roughness is not None and obj.roughness < 0:
        result.add_error("OBJ_ROUGHNESS_NEG", "Шероховатость не может быть отрицательной", "roughness")

    if (
        obj.surface_temperature is not None
        and obj.dew_point is not None
        and obj.surface_temperature <= obj.dew_point
    ):
        result.add_error(
            "OBJ_DEW_POINT",
            f"Температура поверхности ({obj.surface_temperature} °C) не выше точки росы ({obj.dew_point} °C) — нанесение недопустимо",
            "dew_point",
        )

    if obj.dew_point_margin_c is not None and obj.dew_point_margin_c < 0:
        result.add_error("OBJ_DEW_MARGIN_NEG", "Запас до точки росы не может быть отрицательным", "dew_point_margin_c")

    return result


def validate_system_layers(
    layers: Sequence[LayerDefinition | LayerResult],
    compatibility_checker=None,
    system: CoatingSystem | None = None,
) -> ValidationResult:
    """Проверка набора слоёв системы, включая суммарную толщину."""
    result = ValidationResult()

    if not layers:
        result.add_error("SYS_NO_LAYERS", "Система не содержит слоёв")
        return result

    prev_binder: str | None = None
    total_target_dft = 0.0
    total_min_dft = 0.0
    total_max_dft: float | None = 0.0

    for i, layer in enumerate(layers):
        if isinstance(layer, LayerResult):
            material = layer.material
            binder = material.binder_type.value if material else ""
            dft = layer.target_dft
            dft_min = material.recommended_dft_min if material else None
            dft_max = material.recommended_dft_max if material else None
        else:
            material = layer.material
            binder = ""
            if material:
                binder = material.binder_type.value if hasattr(material.binder_type, "value") else str(material.binder_type)
            dft = layer.target_dft
            dft_min = layer.dft_min if layer.dft_min is not None else (material.recommended_dft_min if material else None)
            dft_max = layer.dft_max if layer.dft_max is not None else (material.recommended_dft_max if material else None)

        if material is None and isinstance(layer, LayerDefinition) and layer.material_id is None:
            result.add_error("SYS_LAYER_NO_MATERIAL", f"Слой {i + 1}: не указан материал", layer_index=i)

        if dft < 0:
            result.add_error("SYS_LAYER_DFT_NEG", f"Слой {i + 1}: толщина не может быть отрицательной", "target_dft", i)
        else:
            total_target_dft += dft
            if dft_min is not None:
                total_min_dft += max(0.0, dft_min)
            else:
                total_min_dft = 0.0
            if total_max_dft is not None:
                if dft_max is None:
                    total_max_dft = None
                else:
                    total_max_dft += max(0.0, dft_max)

        if compatibility_checker and prev_binder and binder:
            status = compatibility_checker(prev_binder, binder)
            if status == CompatibilityStatus.FORBIDDEN.value:
                result.add_error(
                    "SYS_COMPAT_FORBIDDEN",
                    f"Слои {i}/{i + 1}: сочетание связующих «{prev_binder}» → «{binder}» запрещено",
                    layer_index=i,
                )
            elif status == CompatibilityStatus.WARNING.value:
                result.add_warning(
                    "SYS_COMPAT_WARNING",
                    f"Слои {i}/{i + 1}: сочетание «{prev_binder}» → «{binder}» требует проверки",
                    layer_index=i,
                )
            elif status == CompatibilityStatus.UNKNOWN.value:
                result.add_info(
                    "SYS_COMPAT_UNKNOWN",
                    f"Слои {i}/{i + 1}: нет подтверждённых данных о совместимости «{prev_binder}» → «{binder}»",
                    layer_index=i,
                )

        if binder:
            prev_binder = binder

    if system is not None:
        if system.number_of_layers and system.number_of_layers != len(layers):
            result.add_error(
                "SYS_LAYER_COUNT",
                f"В системе заявлено {system.number_of_layers} слоёв, фактически задано {len(layers)}",
                "number_of_layers",
            )
        if system.total_dft_min is not None and total_target_dft < system.total_dft_min:
            result.add_error(
                "SYS_TOTAL_DFT_BELOW_MIN",
                f"Суммарная расчётная толщина {total_target_dft:g} мкм ниже минимума системы {system.total_dft_min:g} мкм",
                "total_dft_target",
            )
        if system.total_dft_max is not None and total_target_dft > system.total_dft_max:
            result.add_error(
                "SYS_TOTAL_DFT_ABOVE_MAX",
                f"Суммарная расчётная толщина {total_target_dft:g} мкм выше максимума системы {system.total_dft_max:g} мкм",
                "total_dft_target",
            )
        if system.total_dft_target is not None and abs(total_target_dft - system.total_dft_target) > 1e-9:
            result.add_info(
                "SYS_TOTAL_DFT_TARGET_DIFF",
                f"Расчётная суммарная толщина {total_target_dft:g} мкм отличается от целевой толщины системы {system.total_dft_target:g} мкм",
                "total_dft_target",
            )

    return result


def validate_before_calculation(
    obj: ObjectData,
    layers: Sequence[tuple[Material, float, float, float]],  # (material, dft, losses, thinner%)
    compatibility_checker=None,
) -> ValidationResult:
    """Полная проверка перед запуском расчёта."""
    result = ValidationResult()
    result.merge(validate_object_data(obj))

    if not layers:
        result.add_error("CALC_NO_LAYERS", "Не задано ни одного слоя для расчёта")
        return result

    defs = []
    for i, (material, dft, losses, thinner_pct) in enumerate(layers):
        result.merge(validate_layer_input(material, dft, losses, thinner_pct, layer_index=i))
        result.merge(validate_application_conditions(obj, material, layer_index=i))
        defs.append(LayerDefinition(material=material, target_dft=dft, thinner_percent=thinner_pct))

    if compatibility_checker:
        result.merge(validate_system_layers(defs, compatibility_checker))

    return result
