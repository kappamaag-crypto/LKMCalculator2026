"""Технологический контроль нанесения ЛКМ.

Сервис не изменяет расчёт расхода и не зависит от UI/ORM. Он оценивает
фактические условия нанесения и измеренную DFT относительно требований
материала. Запас до точки росы ниже требуемого является блокирующей ошибкой.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.domain.models import Material, ObjectData


@dataclass(frozen=True)
class TechnologyIssue:
    level: str  # info | warning | error
    code: str
    message: str
    field: Optional[str] = None


@dataclass
class TechnologyCheckResult:
    issues: list[TechnologyIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.level == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.level == "warning" for issue in self.issues)

    @property
    def blocking(self) -> bool:
        return self.has_errors

    def add(self, level: str, code: str, message: str, field: str | None = None) -> None:
        self.issues.append(TechnologyIssue(level, code, message, field))

    def add_error(self, code: str, message: str, field: str | None = None) -> None:
        self.add("error", code, message, field)

    def add_warning(self, code: str, message: str, field: str | None = None) -> None:
        self.add("warning", code, message, field)

    def add_info(self, code: str, message: str, field: str | None = None) -> None:
        self.add("info", code, message, field)


def check_application_technology(
    obj: ObjectData,
    material: Material,
    actual_dft: Optional[float] = None,
) -> TechnologyCheckResult:
    """Проверить условия нанесения и фактическую толщину покрытия.

    Отсутствующие значения не считаются нулём: если их нельзя проверить,
    добавляется информационное сообщение. Это позволяет отличать UNKNOWN
    от реального нарушения технологии.
    """
    result = TechnologyCheckResult()

    surface_temperature = obj.surface_temperature
    if surface_temperature is None:
        surface_temperature = obj.air_temperature
        if surface_temperature is not None:
            result.add_info("COND_SURFACE_TEMP_FALLBACK", "Температура поверхности не задана; использована температура воздуха.", "surface_temperature")

    if surface_temperature is not None:
        if material.min_application_temperature is not None and surface_temperature < material.min_application_temperature:
            result.add_error(
                "TECH_TEMP_BELOW_MIN",
                f"Температура {surface_temperature:g} °C ниже минимальной для «{material.material_name}» ({material.min_application_temperature:g} °C).",
                "surface_temperature",
            )
        if material.max_application_temperature is not None and surface_temperature > material.max_application_temperature:
            result.add_error(
                "TECH_TEMP_ABOVE_MAX",
                f"Температура {surface_temperature:g} °C выше максимальной для «{material.material_name}» ({material.max_application_temperature:g} °C).",
                "surface_temperature",
            )

    if obj.relative_humidity is not None and material.max_relative_humidity is not None:
        if obj.relative_humidity > material.max_relative_humidity:
            result.add_error(
                "TECH_RH_ABOVE_MAX",
                f"Относительная влажность {obj.relative_humidity:g} % превышает допустимые {material.max_relative_humidity:g} %.",
                "relative_humidity",
            )
        else:
            result.add_info("TECH_RH_OK", "Относительная влажность соответствует заданному пределу.", "relative_humidity")
    elif obj.relative_humidity is None:
        result.add_info("TECH_RH_UNKNOWN", "Относительная влажность не задана — проверка RH невозможна.", "relative_humidity")

    if obj.surface_temperature is not None and obj.dew_point is not None:
        margin = obj.surface_temperature - obj.dew_point
        required = material.min_dew_point_margin_c if material.min_dew_point_margin_c is not None else 3.0
        if margin < required:
            result.add_error(
                "TECH_DEW_POINT_MARGIN",
                f"Запас до точки росы {margin:.1f} °C меньше требуемого {required:.1f} °C — нанесение блокируется.",
                "dew_point_margin_c",
            )
        else:
            result.add_info("TECH_DEW_POINT_OK", f"Запас до точки росы {margin:.1f} °C соответствует требованию {required:.1f} °C.", "dew_point_margin_c")
    elif obj.surface_temperature is not None or obj.dew_point is not None:
        result.add_warning("TECH_DEW_POINT_INCOMPLETE", "Для проверки точки росы нужны одновременно температура поверхности и точка росы.", "dew_point")

    if actual_dft is None:
        result.add_info("TECH_DFT_UNKNOWN", "Фактическая DFT не задана — контроль толщины по факту не выполнен.", "actual_dft")
    elif actual_dft < 0:
        result.add_error("TECH_DFT_NEGATIVE", "Фактическая DFT не может быть отрицательной.", "actual_dft")
    else:
        if material.recommended_dft_min is not None and actual_dft < material.recommended_dft_min:
            result.add_error("TECH_DFT_BELOW_MIN", f"Фактическая DFT {actual_dft:g} мкм ниже минимума {material.recommended_dft_min:g} мкм.", "actual_dft")
        if material.recommended_dft_max is not None and actual_dft > material.recommended_dft_max:
            result.add_warning("TECH_DFT_ABOVE_RECOMMENDED", f"Фактическая DFT {actual_dft:g} мкм выше рекомендуемого максимума {material.recommended_dft_max:g} мкм.", "actual_dft")
        if material.max_single_layer_dft is not None and actual_dft > material.max_single_layer_dft:
            result.add_error("TECH_DFT_ABOVE_ABSOLUTE_MAX", f"Фактическая DFT {actual_dft:g} мкм выше абсолютного максимума {material.max_single_layer_dft:g} мкм.", "actual_dft")

    return result
