"""Compliance-first engineering filter for AKZ coating systems.

The filter intentionally separates hard compliance from scoring:
1) ISO 12944 category/durability;
2) system metadata and layer DFT limits;
3) application conditions from the actual object data;
4) missing critical evidence is reported as insufficient data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.enums import CorrosionCategory, DurabilityLevel
from app.domain.models import CoatingSystem, ObjectData


DURABILITY_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}


@dataclass
class EngineeringFilterResult:
    system: CoatingSystem
    status: str = "Подходит"
    passed_checks: list[str] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    insufficient_data: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "Подходит"

    @property
    def has_insufficient_data(self) -> bool:
        return bool(self.insufficient_data)


def _value(value) -> str:
    return "" if value is None else (value.value if hasattr(value, "value") else str(value))


def _check_category(system: CoatingSystem, required: Optional[CorrosionCategory], result: EngineeringFilterResult) -> None:
    if required is None:
        return
    req = _value(required)
    actual = {_value(x) for x in system.corrosion_categories}
    if not actual:
        result.insufficient_data.append(f"Не указана категория коррозии системы; требуется {req}")
    elif req in actual:
        result.passed_checks.append(f"Категория {req}")
    else:
        result.failed_checks.append(f"Категория {req} не заявлена системой (заявлено: {', '.join(sorted(actual))})")


def _check_durability(system: CoatingSystem, required: Optional[DurabilityLevel], result: EngineeringFilterResult) -> None:
    if required is None:
        return
    if system.durability is None:
        result.insufficient_data.append(f"Не указана долговечность системы; требуется {_value(required)}")
        return
    actual = DURABILITY_ORDER.get(_value(system.durability), 0)
    needed = DURABILITY_ORDER.get(_value(required), 0)
    if actual >= needed:
        result.passed_checks.append(f"Долговечность {_value(system.durability)} ≥ {_value(required)}")
    else:
        result.failed_checks.append(f"Долговечность {_value(system.durability)} ниже требуемой {_value(required)}")


def _check_temperature(system: CoatingSystem, obj: ObjectData, result: EngineeringFilterResult) -> None:
    if obj.temperature_min is None and obj.temperature_max is None:
        return
    if system.temperature_min is None and system.temperature_max is None:
        result.insufficient_data.append("Не указан диапазон эксплуатационной температуры системы")
        return
    if obj.temperature_min is not None and system.temperature_min is not None and obj.temperature_min < system.temperature_min:
        result.failed_checks.append(f"Минимальная температура объекта {obj.temperature_min} °C ниже допуска системы {system.temperature_min} °C")
    if obj.temperature_max is not None and system.temperature_max is not None and obj.temperature_max > system.temperature_max:
        result.failed_checks.append(f"Максимальная температура объекта {obj.temperature_max} °C выше допуска системы {system.temperature_max} °C")
    if not result.failed_checks:
        result.passed_checks.append("Эксплуатационный температурный диапазон")


def _check_surface_and_environment(system: CoatingSystem, obj: ObjectData, result: EngineeringFilterResult) -> None:
    if obj.surface_type is not None:
        actual = {_value(x) for x in system.surface_types}
        if not actual:
            result.insufficient_data.append("Не указаны допустимые типы поверхности")
        elif _value(obj.surface_type) not in actual:
            result.failed_checks.append(f"Тип поверхности {_value(obj.surface_type)} не заявлен системой")
        else:
            result.passed_checks.append("Тип поверхности")
    if obj.environment is not None:
        actual = {_value(x) for x in system.environments}
        if not actual:
            result.insufficient_data.append("Не указана эксплуатационная среда")
        elif _value(obj.environment) not in actual:
            result.failed_checks.append(f"Среда {_value(obj.environment)} не заявлена системой")
        else:
            result.passed_checks.append("Эксплуатационная среда")


def _check_layers(system: CoatingSystem, obj: ObjectData, result: EngineeringFilterResult) -> None:
    if not system.layers:
        result.failed_checks.append("В системе отсутствуют слои")
        return
    if system.number_of_layers and system.number_of_layers != len(system.layers):
        result.failed_checks.append(f"Несоответствие числа слоёв: метаданные {system.number_of_layers}, фактически {len(system.layers)}")

    total_target = 0.0
    for index, layer in enumerate(system.layers, 1):
        material = layer.material
        if material is None:
            result.insufficient_data.append(f"Слой {index}: материал не загружен")
            continue
        target = layer.target_dft or 0.0
        total_target += target
        if target <= 0:
            result.insufficient_data.append(f"Слой {index}: не задана целевая DFT")
        if material.recommended_dft_min is not None and target > 0 and target < material.recommended_dft_min:
            result.failed_checks.append(f"Слой {index}: DFT {target:g} мкм ниже минимума материала {material.recommended_dft_min:g} мкм")
        if material.recommended_dft_max is not None and target > material.recommended_dft_max:
            result.failed_checks.append(f"Слой {index}: DFT {target:g} мкм выше максимума материала {material.recommended_dft_max:g} мкм")
        if material.max_single_layer_dft is not None and target > material.max_single_layer_dft:
            result.failed_checks.append(f"Слой {index}: DFT {target:g} мкм выше абсолютного максимума {material.max_single_layer_dft:g} мкм")

        if obj.application_method and material.application_method and obj.application_method != material.application_method:
            result.failed_checks.append(f"Слой {index}: способ нанесения не соответствует ТДС материала")
        if obj.surface_temperature is not None:
            if material.min_application_temperature is not None and obj.surface_temperature < material.min_application_temperature:
                result.failed_checks.append(f"Слой {index}: температура поверхности ниже {material.min_application_temperature:g} °C")
            if material.max_application_temperature is not None and obj.surface_temperature > material.max_application_temperature:
                result.failed_checks.append(f"Слой {index}: температура поверхности выше {material.max_application_temperature:g} °C")
        if obj.relative_humidity is not None and material.max_relative_humidity is not None and obj.relative_humidity > material.max_relative_humidity:
            result.failed_checks.append(f"Слой {index}: RH {obj.relative_humidity:g}% выше допуска {material.max_relative_humidity:g}%")
        if obj.surface_temperature is not None and obj.dew_point is not None:
            required_margin = material.min_dew_point_margin_c if material.min_dew_point_margin_c is not None else 3.0
            actual_margin = obj.surface_temperature - obj.dew_point
            if actual_margin < required_margin:
                result.failed_checks.append(f"Слой {index}: запас до точки росы {actual_margin:.1f} °C < {required_margin:.1f} °C")

    if system.total_dft_min is not None and total_target < system.total_dft_min:
        result.failed_checks.append(f"Суммарная DFT {total_target:g} мкм ниже минимума системы {system.total_dft_min:g} мкм")
    if system.total_dft_max is not None and total_target > system.total_dft_max:
        result.failed_checks.append(f"Суммарная DFT {total_target:g} мкм выше максимума системы {system.total_dft_max:g} мкм")
    if system.total_dft_target is not None and total_target:
        result.passed_checks.append(f"Суммарная DFT {total_target:g} мкм; целевая {system.total_dft_target:g} мкм")


def evaluate_system(system: CoatingSystem, obj: ObjectData) -> EngineeringFilterResult:
    """Evaluate one system without any price-based scoring."""
    result = EngineeringFilterResult(system=system)
    _check_category(system, obj.corrosion_category, result)
    _check_durability(system, obj.durability, result)
    _check_surface_and_environment(system, obj, result)
    _check_temperature(system, obj, result)
    _check_layers(system, obj, result)

    if result.failed_checks:
        result.status = "Не подходит"
    elif result.insufficient_data:
        result.status = "Недостаточно данных"
    else:
        result.status = "Подходит"
    return result


def evaluate_systems(systems: Sequence[CoatingSystem], obj: ObjectData) -> list[EngineeringFilterResult]:
    return [evaluate_system(system, obj) for system in systems]
