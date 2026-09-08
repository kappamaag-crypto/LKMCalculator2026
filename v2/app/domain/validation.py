"""
Валидация входных данных и результатов расчёта.
Все сообщения — на русском языке.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import (
    Material, LayerDefinition, LayerResult, CoatingSystem, ObjectData, SystemCalculationResult,
)
from app.domain.enums import CompatibilityStatus


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
    result = ValidationResult()
    if not material.material_name or not material.material_name.strip():
        result.add_error("MAT_NAME", "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430", "material_name")
    if material.density is not None and material.density < 0:
        result.add_error("MAT_DENSITY_NEG", "\u041f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043e\u0442\u0440\u0438\u0446\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0439", "density")
    if material.density == 0 and getattr(material.material_type, "value", "") != "\u0440\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c":
        result.add_warning("MAT_DENSITY_ZERO", "\u041f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c \u0440\u0430\u0432\u043d\u0430 \u043d\u0443\u043b\u044e", "density")
    if material.solids_percent is not None:
        if material.solids_percent < 0:
            result.add_error("MAT_SOLIDS_NEG", "\u0421\u0443\u0445\u043e\u0439 \u043e\u0441\u0442\u0430\u0442\u043e\u043a \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043e\u0442\u0440\u0438\u0446\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u043c", "solids_percent")
        if material.solids_percent > 100:
            result.add_error("MAT_SOLIDS_GT100", "\u0421\u0443\u0445\u043e\u0439 \u043e\u0441\u0442\u0430\u0442\u043e\u043a \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u0435\u0432\u044b\u0448\u0430\u0442\u044c 100 %", "solids_percent")
        if material.solids_percent == 0 and getattr(material.material_type, "value", "") != "\u0440\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c":
            result.add_warning("MAT_SOLIDS_ZERO", "\u0421\u0443\u0445\u043e\u0439 \u043e\u0441\u0442\u0430\u0442\u043e\u043a = 0 %", "solids_percent")
    if material.price_per_kg is not None and material.price_per_kg < 0:
        result.add_error("MAT_PRICE_NEG", "\u0426\u0435\u043d\u0430 \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043e\u0442\u0440\u0438\u0446\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0439", "price_per_kg")
    if material.recommended_dft_min is not None and material.recommended_dft_max is not None:
        if material.recommended_dft_min > material.recommended_dft_max:
            result.add_error("MAT_DFT_RANGE", "DFT min > DFT max", "recommended_dft")
    return result


def validate_layer_input(
    material: Material, target_dft: float, losses_percent: float = 0.0,
    thinner_percent: float = 0.0, layer_index: int | None = None,
) -> ValidationResult:
    result = ValidationResult()
    mat_result = validate_material(material)
    for issue in mat_result.issues:
        issue.layer_index = layer_index
        result.issues.append(issue)
    if target_dft < 0:
        result.add_error("LAYER_DFT_NEG", "DFT \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043e\u0442\u0440\u0438\u0446\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0439", "target_dft", layer_index)
    if target_dft == 0:
        result.add_warning("LAYER_DFT_ZERO", "DFT = 0", "target_dft", layer_index)
    if losses_percent < 0:
        result.add_error("LAYER_LOSSES_NEG", "\u041f\u043e\u0442\u0435\u0440\u0438 < 0", "losses_percent", layer_index)
    if losses_percent >= 100:
        result.add_error("LAYER_LOSSES_GE100", "\u041f\u043e\u0442\u0435\u0440\u0438 \u2265 100 %", "losses_percent", layer_index)
    if thinner_percent < 0:
        result.add_error("LAYER_THINNER_NEG", "\u0420\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c < 0", "thinner_percent", layer_index)
    if thinner_percent > 100:
        result.add_warning("LAYER_THINNER_GT100", "\u0420\u0430\u0437\u0431\u0430\u0432\u0438\u0442\u0435\u043b\u044c > 100 %", "thinner_percent", layer_index)
    if material.recommended_dft_min is not None and 0 < target_dft < material.recommended_dft_min:
        result.add_warning("LAYER_DFT_BELOW_MIN", f"DFT {target_dft} < min {material.recommended_dft_min}", "target_dft", layer_index)
    if material.recommended_dft_max is not None and target_dft > material.recommended_dft_max:
        result.add_warning("LAYER_DFT_ABOVE_MAX", f"DFT {target_dft} > max {material.recommended_dft_max}", "target_dft", layer_index)
    if material.max_single_layer_dft is not None and target_dft > material.max_single_layer_dft:
        result.add_error("LAYER_DFT_MAX_SINGLE", f"DFT {target_dft} > max single {material.max_single_layer_dft}", "target_dft", layer_index)
    return result


def validate_object_data(obj: ObjectData) -> ValidationResult:
    result = ValidationResult()
    if obj.area_m2 < 0:
        result.add_error("OBJ_AREA_NEG", "\u041f\u043b\u043e\u0449\u0430\u0434\u044c < 0", "area_m2")
    if obj.area_m2 == 0 and obj.area_per_element <= 0:
        result.add_warning("OBJ_AREA_ZERO", "\u041f\u043b\u043e\u0449\u0430\u0434\u044c = 0", "area_m2")
    if obj.elements_count < 0:
        result.add_error("OBJ_ELEMENTS_NEG", "\u041a\u043e\u043b-\u0432\u043e \u044d\u043b\u0435\u043c\u0435\u043d\u0442\u043e\u0432 < 0", "elements_count")
    if obj.area_per_element < 0:
        result.add_error("OBJ_AREA_PER_EL_NEG", "\u041f\u043b\u043e\u0449\u0430\u0434\u044c \u044d\u043b\u0435\u043c\u0435\u043d\u0442\u0430 < 0", "area_per_element")
    if obj.surface_temperature is not None and obj.dew_point is not None and obj.surface_temperature <= obj.dew_point:
        result.add_error("OBJ_DEW_POINT", f"T \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438 ({obj.surface_temperature}) <= \u0442\u043e\u0447\u043a\u0438 \u0440\u043e\u0441\u044b ({obj.dew_point})", "dew_point")
    if obj.relative_humidity is not None and (obj.relative_humidity < 0 or obj.relative_humidity > 100):
        result.add_error("OBJ_RH_RANGE", "RH 0\u2013100 %", "relative_humidity")
    return result


def validate_system_layers(layers: Sequence, compatibility_checker=None) -> ValidationResult:
    result = ValidationResult()
    if not layers:
        result.add_error("SYS_NO_LAYERS", "\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u0431\u0435\u0437 \u0441\u043b\u043e\u0451\u0432")
        return result
    prev_binder = None
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
            result.add_error("SYS_LAYER_NO_MATERIAL", f"\u0421\u043b\u043e\u0439 {i+1}: \u043d\u0435\u0442 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430", layer_index=i)
        if compatibility_checker and prev_binder and binder:
            status = compatibility_checker(prev_binder, binder)
            if status == CompatibilityStatus.FORBIDDEN.value:
                result.add_error("SYS_COMPAT_FORBIDDEN", f"\u0421\u043b\u043e\u0438 {i}/{i+1}: {prev_binder} \u2192 {binder} \u0437\u0430\u043f\u0440\u0435\u0449\u0435\u043d\u043e", layer_index=i)
            elif status == CompatibilityStatus.WARNING.value:
                result.add_warning("SYS_COMPAT_WARNING", f"\u0421\u043b\u043e\u0438 {i}/{i+1}: {prev_binder} \u2192 {binder} \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430", layer_index=i)
        if binder:
            prev_binder = binder
    return result


def validate_before_calculation(
    obj: ObjectData,
    layers: Sequence[tuple],
    compatibility_checker=None,
) -> ValidationResult:
    result = ValidationResult()
    result.merge(validate_object_data(obj))
    if not layers:
        result.add_error("CALC_NO_LAYERS", "\u041d\u0435\u0442 \u0441\u043b\u043e\u0451\u0432")
        return result
    for i, (material, dft, losses, thinner_pct) in enumerate(layers):
        result.merge(validate_layer_input(material, dft, losses, thinner_pct, layer_index=i))
    if compatibility_checker:
        defs = [LayerDefinition(material=m, target_dft=d, thinner_percent=t) for m, d, _, t in layers]
        result.merge(validate_system_layers(defs, compatibility_checker))
    return result
