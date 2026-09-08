"""
Валидация входных данных и результатов расчёта.

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
    """Проверка материала."""
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

    if material.price_per_kg is not None and material.price_per_kg < 0:
        result.add_error("MAT_PRICE_NEG", "Цена не может быть отрицательной", "price_per_kg")

    if material.recommended_dft_min is not None and material.recommended_dft_max is not None:
        if material.recommended_dft_min > material.recommended_dft_max:
            result.add_error(
                "MAT_DFT_RANGE",
                f"Минимальная рекомендуемая толщина ({material.recommended_dft_min}) "
                f"больше максимальной ({material.recommended_dft_max})",
                "recommended_dft",
            )

    return result


def validate_layer_input(
    material: Material,
    target_dft: float,
    losses_percent: float = 0.0,
    thinner_percent: float = 0.0,
    layer_index: int | None = None,
) -> ValidationResult:
    """Проверка входных данных слоя перед расчётом."""
    result = ValidationResult()

    mat_result = validate_material(material)
    # Переносим issues с привязкой к слою
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
        result.add_warning("LAYER_THINNER_GT100", "Процент разбавителя превышает 100 %", "thinner_percent", layer_index)

    # Проверка выхода за рекомендуемый диапазон DFT
    if material.recommended_dft_min is not None and target_dft > 0:
        if target_dft < material.recommended_dft_min:
            result.add_warning(
                "LAYER_DFT_BELOW_MIN",
                f"Толщина {target_dft} мкм ниже рекомендуемого минимума "
                f"({material.recommended_dft_min} мкм) для «{material.material_name}»",
                "target_dft",
                layer_index,
            )
    if material.recommended_dft_max is not None and target_dft > 0:
        if target_dft > material.recommended_dft_max:
            result.add_warning(
                "LAYER_DFT_ABOVE_MAX",
                f"Толщина {target_dft} мкм выше рекомендуемого максимума "
                f"({material.recommended_dft_max} мкм) для «{material.material_name}»",
                "target_dft",
                layer_index,
            )
    if material.max_single_layer_dft is not None and target_dft > material.max_single_layer_dft:
        result.add_error(
            "LAYER_DFT_MAX_SINGLE",
            f"Толщина {target_dft} мкм превышает максимальную толщину одного слоя "
            f"({material.max_single_layer_dft} мкм) для «{material.material_name}»",
            "target_dft",
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

    # Точка росы
    if (
        obj.surface_temperature is not None
        and obj.dew_point is not None
        and obj.surface_temperature <= obj.dew_point
    ):
        result.add_error(
            "OBJ_DEW_POINT",
            f"Температура поверхности ({obj.surface_temperature} °C) "
            f"не выше точки росы ({obj.dew_point} °C) — нанесение недопустимо",
            "dew_point",
        )

    if obj.relative_humidity is not None:
        if obj.relative_humidity < 0 or obj.relative_humidity > 100:
            result.add_error("OBJ_RH_RANGE", "Относительная влажность должна быть в диапазоне 0–100 %", "relative_humidity")

    return result


def validate_system_layers(
    layers: Sequence[LayerDefinition | LayerResult],
    compatibility_checker=None,
) -> ValidationResult:
    """
    Проверка набора слоёв системы.

    compatibility_checker: callable(from_binder, to_binder) -> str (status)
    """
    result = ValidationResult()

    if not layers:
        result.add_error("SYS_NO_LAYERS", "Система не содержит слоёв")
        return result

    prev_binder: str | None = None
    for i, layer in enumerate(layers):
        if isinstance(layer, LayerResult):
            material = layer.material
            binder = material.binder_type.value if material else ""
        else:
            material = layer.material
            binder = ""
            if material:
                binder = material.binder_type.value if hasattr(material.binder_type, "value") else str(material.binder_type)

        if material is None and isinstance(layer, LayerDefinition) and layer.material_id is None:
            result.add_error("SYS_LAYER_NO_MATERIAL", f"Слой {i + 1}: не указан материал", layer_index=i)

        # Совместимость
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

    return result


def validate_before_calculation(
    obj: ObjectData,
    layers: Sequence[tuple[Material, float, float, float]],  # (material, dft, losses, thinner%)
    compatibility_checker=None,
) -> ValidationResult:
    """
    Полная проверка перед запуском расчёта.

    layers: список кортежей (material, target_dft, losses_percent, thinner_percent)
    """
    result = ValidationResult()
    result.merge(validate_object_data(obj))

    if not layers:
        result.add_error("CALC_NO_LAYERS", "Не задано ни одного слоя для расчёта")
        return result

    for i, (material, dft, losses, thinner_pct) in enumerate(layers):
        result.merge(validate_layer_input(material, dft, losses, thinner_pct, layer_index=i))

    # Совместимость по binder
    if compatibility_checker:
        defs = []
        for material, dft, losses, thinner_pct in layers:
            ld = LayerDefinition(material=material, target_dft=dft, thinner_percent=thinner_pct)
            defs.append(ld)
        result.merge(validate_system_layers(defs, compatibility_checker))

    return result