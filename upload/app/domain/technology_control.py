"""Технологический контроль нанесения ЛКМ/АКЗ.

Модуль не выполняет расчёт расхода и не содержит UI-логики. Он проверяет
условия нанесения и фактическую толщину относительно требований материала.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import Material, ObjectData


INFO = "info"
WARNING = "warning"
ERROR = "error"


@dataclass(frozen=True)
class TechnologyIssue:
    level: str
    code: str
    message: str
    layer_index: Optional[int] = None


@dataclass
class TechnologyCheckResult:
    issues: list[TechnologyIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.level == ERROR for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.level == WARNING for issue in self.issues)

    @property
    def errors(self) -> list[TechnologyIssue]:
        return [issue for issue in self.issues if issue.level == ERROR]

    @property
    def warnings(self) -> list[TechnologyIssue]:
        return [issue for issue in self.issues if issue.level == WARNING]

    def add(self, level: str, code: str, message: str, layer_index: int | None = None) -> None:
        self.issues.append(TechnologyIssue(level, code, message, layer_index))


class TechnologyCheckService:
    """Проверяет технологические условия до/между/после нанесения."""

    def check_application_conditions(
        self,
        obj: ObjectData,
        materials: Sequence[Material],
        required_dew_point_margin_c: float | None = None,
    ) -> TechnologyCheckResult:
        result = TechnologyCheckResult()

        self._check_rh(result, obj.relative_humidity, materials)
        self._check_air_temperature(result, obj.air_temperature, materials)
        self._check_surface_temperature(result, obj.surface_temperature, materials)
        self._check_dew_point(result, obj, materials, required_dew_point_margin_c)

        if obj.roughness is None:
            result.add(INFO, "ROUGHNESS_UNKNOWN", "Шероховатость поверхности не задана.")
        if obj.preparation is None:
            result.add(INFO, "PREPARATION_UNKNOWN", "Степень подготовки поверхности не задана.")
        if obj.surface_temperature is None:
            result.add(INFO, "SURFACE_TEMP_UNKNOWN", "Температура поверхности не задана.")
        if obj.air_temperature is None:
            result.add(INFO, "AIR_TEMP_UNKNOWN", "Температура воздуха не задана.")
        if obj.relative_humidity is None:
            result.add(INFO, "RH_UNKNOWN", "Относительная влажность не задана.")

        return result

    def check_dft(
        self,
        material: Material,
        actual_dft: float | None,
        layer_index: int | None = None,
    ) -> TechnologyCheckResult:
        result = TechnologyCheckResult()
        if actual_dft is None:
            result.add(INFO, "DFT_ACTUAL_UNKNOWN", "Фактическая DFT не задана.", layer_index)
            return result
        if actual_dft < 0:
            result.add(ERROR, "DFT_ACTUAL_NEGATIVE", "Фактическая DFT не может быть отрицательной.", layer_index)
            return result

        if material.recommended_dft_min is not None and actual_dft < material.recommended_dft_min:
            result.add(
                ERROR,
                "DFT_BELOW_MIN",
                f"Фактическая DFT {actual_dft:g} мкм ниже минимальной {material.recommended_dft_min:g} мкм.",
                layer_index,
            )

        if material.recommended_dft_max is not None and actual_dft > material.recommended_dft_max:
            result.add(
                WARNING,
                "DFT_ABOVE_RECOMMENDED_MAX",
                f"Фактическая DFT {actual_dft:g} мкм выше рекомендуемого максимума {material.recommended_dft_max:g} мкм.",
                layer_index,
            )

        if material.max_single_layer_dft is not None and actual_dft > material.max_single_layer_dft:
            result.add(
                ERROR,
                "DFT_ABOVE_SINGLE_LAYER_MAX",
                f"Фактическая DFT {actual_dft:g} мкм превышает допустимый максимум одного слоя {material.max_single_layer_dft:g} мкм.",
                layer_index,
            )

        return result

    def check_total_dft(
        self,
        actual_dft: float | None,
        minimum: float | None,
        maximum: float | None,
    ) -> TechnologyCheckResult:
        result = TechnologyCheckResult()
        if actual_dft is None:
            result.add(INFO, "TOTAL_DFT_UNKNOWN", "Фактическая общая DFT не задана.")
            return result
        if minimum is not None and actual_dft < minimum:
            result.add(ERROR, "TOTAL_DFT_BELOW_MIN", f"Общая DFT {actual_dft:g} мкм ниже минимума {minimum:g} мкм.")
        if maximum is not None and actual_dft > maximum:
            result.add(WARNING, "TOTAL_DFT_ABOVE_MAX", f"Общая DFT {actual_dft:g} мкм выше максимума {maximum:g} мкм.")
        return result

    def check_recoat_interval(
        self,
        material: Material,
        elapsed_hours: float,
        layer_index: int | None = None,
    ) -> TechnologyCheckResult:
        result = TechnologyCheckResult()
        if elapsed_hours < 0:
            result.add(ERROR, "RECOAT_NEGATIVE", "Межслойная выдержка не может быть отрицательной.", layer_index)
            return result
        if material.min_recoat_time_h is not None and elapsed_hours < material.min_recoat_time_h:
            result.add(
                ERROR,
                "RECOAT_TOO_EARLY",
                f"Нанесение следующего слоя через {elapsed_hours:g} ч раньше минимума {material.min_recoat_time_h:g} ч.",
                layer_index,
            )
        if material.max_recoat_time_h is not None and elapsed_hours > material.max_recoat_time_h:
            result.add(
                WARNING,
                "RECOAT_TOO_LATE",
                f"Межслойная выдержка {elapsed_hours:g} ч превышает рекомендуемый максимум {material.max_recoat_time_h:g} ч.",
                layer_index,
            )
        return result

    @staticmethod
    def _check_rh(result: TechnologyCheckResult, rh: float | None, materials: Sequence[Material]) -> None:
        if rh is None:
            return
        if not 0 <= rh <= 100:
            result.add(ERROR, "RH_RANGE", f"Относительная влажность {rh:g}% вне диапазона 0–100%.")
            return
        limits = [m.max_relative_humidity for m in materials if m.max_relative_humidity is not None]
        if limits and rh > min(limits):
            result.add(ERROR, "RH_TOO_HIGH", f"RH {rh:g}% превышает допустимый предел {min(limits):g}% для выбранной системы.")

    @staticmethod
    def _check_air_temperature(result: TechnologyCheckResult, temperature: float | None, materials: Sequence[Material]) -> None:
        if temperature is None:
            return
        mins = [m.min_application_temperature for m in materials if m.min_application_temperature is not None]
        maxs = [m.max_application_temperature for m in materials if m.max_application_temperature is not None]
        if mins and temperature < max(mins):
            result.add(ERROR, "AIR_TEMP_TOO_LOW", f"Температура воздуха {temperature:g}°C ниже минимально допустимой {max(mins):g}°C.")
        if maxs and temperature > min(maxs):
            result.add(ERROR, "AIR_TEMP_TOO_HIGH", f"Температура воздуха {temperature:g}°C выше максимально допустимой {min(maxs):g}°C.")

    @staticmethod
    def _check_surface_temperature(result: TechnologyCheckResult, temperature: float | None, materials: Sequence[Material]) -> None:
        if temperature is None:
            return
        mins = [m.min_application_temperature for m in materials if m.min_application_temperature is not None]
        maxs = [m.max_application_temperature for m in materials if m.max_application_temperature is not None]
        if mins and temperature < max(mins):
            result.add(ERROR, "SURFACE_TEMP_TOO_LOW", f"Температура поверхности {temperature:g}°C ниже минимально допустимой {max(mins):g}°C.")
        if maxs and temperature > min(maxs):
            result.add(ERROR, "SURFACE_TEMP_TOO_HIGH", f"Температура поверхности {temperature:g}°C выше максимально допустимой {min(maxs):g}°C.")

    @staticmethod
    def _check_dew_point(
        result: TechnologyCheckResult,
        obj: ObjectData,
        materials: Sequence[Material],
        required_margin_c: float | None,
    ) -> None:
        if obj.surface_temperature is None or obj.dew_point is None:
            return
        margin = obj.surface_temperature - obj.dew_point
        material_margins = [m.min_dew_point_margin_c for m in materials if m.min_dew_point_margin_c is not None]
        required = required_margin_c if required_margin_c is not None else (max(material_margins) if material_margins else 3.0)
        if margin < required:
            result.add(ERROR, "DEW_POINT_MARGIN_FAIL", f"Запас до точки росы {margin:g}°C меньше требуемого {required:g}°C.")
        else:
            result.add(INFO, "DEW_POINT_MARGIN_PASS", f"Запас до точки росы {margin:g}°C соответствует требованию {required:g}°C.")
