"""Pre-Application Check — единый инженерный чеклист до нанесения.

Доменный модуль: не импортирует services/ORM/UI.
Не подставляет скрытые инженерные значения (запас точки росы, DFT и т.п.).
Отсутствующие данные = UNKNOWN / INCOMPLETE, не «пройдено по умолчанию».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import Material, ObjectData
from app.domain.surface_profile import SurfaceCondition
from app.domain.technology import TechnologyCheckResult, TechnologyIssue, check_application_technology


READY = "READY"
BLOCKED = "BLOCKED"
INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class PreApplicationItem:
    """Один пункт чеклиста с кодом и уровнем."""

    code: str
    level: str  # info | warning | error
    message: str
    scope: str = "object"  # object | surface | material
    material_name: str = ""
    field: Optional[str] = None


@dataclass
class PreApplicationCheckResult:
    """Итог Pre-Application Check.

    status:
      READY      — нет ошибок, нет критичных UNKNOWN по условиям нанесения
      BLOCKED    — есть хотя бы одна error
      INCOMPLETE — ошибок нет, но ключевые данные UNKNOWN (нельзя подтвердить готовность)
    """

    items: list[PreApplicationItem] = field(default_factory=list)
    material_results: list[tuple[str, TechnologyCheckResult]] = field(default_factory=list)

    def add(
        self,
        code: str,
        level: str,
        message: str,
        *,
        scope: str = "object",
        material_name: str = "",
        field: str | None = None,
    ) -> None:
        self.items.append(
            PreApplicationItem(
                code=code,
                level=level,
                message=message,
                scope=scope,
                material_name=material_name,
                field=field,
            )
        )

    @property
    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.items) or any(
            r.has_errors for _, r in self.material_results
        )

    @property
    def has_warnings(self) -> bool:
        return any(i.level == "warning" for i in self.items) or any(
            r.has_warnings for _, r in self.material_results
        )

    @property
    def has_blocking_unknown(self) -> bool:
        """Ключевые UNKNOWN, из-за которых нельзя считать READY."""
        incomplete_codes = {
            "PRE_AMBIENT_UNKNOWN",
            "PRE_DEW_POINT_UNKNOWN",
            "PRE_SURFACE_PREP_UNKNOWN",
            "PRE_SURFACE_PROFILE_UNKNOWN",
            "PRE_MATERIAL_LIMITS_UNKNOWN",
        }
        if any(i.code in incomplete_codes for i in self.items):
            return True
        for _, tech in self.material_results:
            for issue in tech.issues:
                if issue.level == "info" and issue.code in {
                    "TECH_DEW_POINT_MARGIN_UNKNOWN",
                    "TECH_RH_UNKNOWN",
                    "TECH_DFT_UNKNOWN",
                }:
                    # DFT unknown alone does not block pre-app readiness for ambient;
                    # dew-point margin UNKNOWN does.
                    if issue.code == "TECH_DEW_POINT_MARGIN_UNKNOWN":
                        return True
        return False

    @property
    def status(self) -> str:
        if self.has_errors:
            return BLOCKED
        if self.has_blocking_unknown:
            return INCOMPLETE
        return READY

    @property
    def ready(self) -> bool:
        return self.status == READY

    def summary_lines(self) -> list[str]:
        lines = [f"Pre-Application: {self.status}"]
        for item in self.items:
            prefix = item.level.upper()
            scope = f"[{item.scope}]"
            mat = f" ({item.material_name})" if item.material_name else ""
            lines.append(f"  {prefix} {scope}{mat} {item.code}: {item.message}")
        for name, tech in self.material_results:
            for issue in tech.issues:
                lines.append(
                    f"  {issue.level.upper()} [material] ({name}) {issue.code}: {issue.message}"
                )
        return lines


def _check_ambient(obj: ObjectData, result: PreApplicationCheckResult) -> None:
    missing = []
    if obj.air_temperature is None and obj.surface_temperature is None:
        missing.append("температура")
    if obj.relative_humidity is None:
        missing.append("RH")
    if obj.dew_point is None and obj.dew_point_margin_c is None:
        missing.append("точка росы / запас")
    if missing:
        result.add(
            "PRE_AMBIENT_UNKNOWN",
            "info",
            "Условия окружающей среды неполны: " + ", ".join(missing) + ".",
            scope="object",
            field="ambient",
        )
    else:
        result.add(
            "PRE_AMBIENT_PRESENT",
            "info",
            "Базовые условия окружающей среды заданы.",
            scope="object",
            field="ambient",
        )

    if obj.surface_temperature is not None and obj.dew_point is not None:
        margin = obj.surface_temperature - obj.dew_point
        if margin < 0:
            result.add(
                "PRE_DEW_POINT_NEGATIVE",
                "error",
                f"Температура поверхности ниже точки росы (запас {margin:g} °C).",
                scope="object",
                field="dew_point",
            )
    elif obj.dew_point is None and obj.dew_point_margin_c is None:
        result.add(
            "PRE_DEW_POINT_UNKNOWN",
            "info",
            "Точка росы / запас не заданы — проверка dew-point margin невозможна.",
            scope="object",
            field="dew_point",
        )


def _check_surface(condition: SurfaceCondition | None, obj: ObjectData, result: PreApplicationCheckResult) -> None:
    if condition is None:
        condition = SurfaceCondition()

    prep = condition.preparation
    if not prep.is_known:
        # fallback to ObjectData.preparation if present
        if obj.preparation is None:
            result.add(
                "PRE_SURFACE_PREP_UNKNOWN",
                "info",
                "Степень подготовки поверхности не подтверждена (UNKNOWN).",
                scope="surface",
                field="preparation",
            )
        else:
            result.add(
                "PRE_SURFACE_PREP_FROM_OBJECT",
                "info",
                f"Подготовка из ObjectData: {obj.preparation}.",
                scope="surface",
                field="preparation",
            )
    else:
        result.add(
            "PRE_SURFACE_PREP_KNOWN",
            "info",
            f"Подготовка KNOWN: {prep.grade or '—'} ({prep.standard.document_id if prep.standard else '—'}).",
            scope="surface",
            field="preparation",
        )

    profile = condition.profile
    if not profile.is_known and not profile.is_measured:
        if obj.roughness is None:
            result.add(
                "PRE_SURFACE_PROFILE_UNKNOWN",
                "info",
                "Профиль поверхности / шероховатость не заданы (UNKNOWN).",
                scope="surface",
                field="profile",
            )
        else:
            result.add(
                "PRE_SURFACE_PROFILE_FROM_OBJECT",
                "info",
                f"Шероховатость из ObjectData: {obj.roughness:g}.",
                scope="surface",
                field="profile",
            )
    else:
        result.add(
            "PRE_SURFACE_PROFILE_KNOWN",
            "info",
            "Профиль поверхности задан или KNOWN.",
            scope="surface",
            field="profile",
        )

    if condition.contamination_status == "UNACCEPTABLE":
        result.add(
            "PRE_SURFACE_CONTAMINATION",
            "error",
            "Загрязнение поверхности: UNACCEPTABLE.",
            scope="surface",
            field="contamination",
        )
    if condition.moisture_status == "UNACCEPTABLE":
        result.add(
            "PRE_SURFACE_MOISTURE",
            "error",
            "Влажность поверхности: UNACCEPTABLE.",
            scope="surface",
            field="moisture",
        )


def check_pre_application(
    obj: ObjectData,
    materials: Sequence[Material],
    *,
    surface_condition: SurfaceCondition | None = None,
    actual_dfts: Sequence[Optional[float]] | None = None,
) -> PreApplicationCheckResult:
    """Выполнить Pre-Application Check для объекта и набора материалов.

    actual_dfts — опциональные фактические/целевые DFT по слоям (длина = len(materials)).
    Не подставляет min_dew_point_margin_c=3 и не использует TDS без явной передачи через Material.
    """
    result = PreApplicationCheckResult()
    _check_ambient(obj, result)
    _check_surface(surface_condition, obj, result)

    if not materials:
        result.add(
            "PRE_NO_MATERIALS",
            "warning",
            "Материалы для проверки не переданы.",
            scope="object",
        )
        return result

    dfts = list(actual_dfts) if actual_dfts is not None else [None] * len(materials)
    while len(dfts) < len(materials):
        dfts.append(None)

    limits_unknown = 0
    for material, dft in zip(materials, dfts):
        name = material.material_name or material.display_name()
        tech = check_application_technology(obj, material, actual_dft=dft)
        result.material_results.append((name, tech))

        has_temp_limits = (
            material.min_application_temperature is not None
            or material.max_application_temperature is not None
        )
        has_rh_limit = material.max_relative_humidity is not None
        has_dew_limit = material.min_dew_point_margin_c is not None
        if not (has_temp_limits or has_rh_limit or has_dew_limit):
            limits_unknown += 1
            result.add(
                "PRE_MATERIAL_LIMITS_UNKNOWN",
                "info",
                f"У материала «{name}» нет KNOWN технологических пределов (T/RH/dew-point) — проверка условий ограничена.",
                scope="material",
                material_name=name,
            )

    if limits_unknown == len(materials) and materials:
        # already added per-material; overall note is enough via has_blocking_unknown
        pass

    return result
