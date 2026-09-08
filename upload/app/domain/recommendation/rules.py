"""Правила фильтрации систем АКЗ (этап hard-filter рекомендаций).

Система сначала проходит жёсткие инженерные проверки, затем может участвовать
в скоринге. Предположения по отсутствующим данным не делаются.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import CoatingSystem, ObjectData
from app.domain.enums import CorrosionCategory, DurabilityLevel, SurfaceType, EnvironmentType
from app.domain.technology import check_application_technology, check_target_dft


@dataclass
class FilterResult:
    system: CoatingSystem
    passed: bool
    reasons_pass: list[str] = field(default_factory=list)
    reasons_fail: list[str] = field(default_factory=list)
    insufficient_data: bool = False
    notes: list[str] = field(default_factory=list)


def _cat_value(cat) -> str:
    return "" if cat is None else (cat.value if hasattr(cat, "value") else str(cat))


def _dur_value(dur) -> str:
    return "" if dur is None else (dur.value if hasattr(dur, "value") else str(dur))


DURABILITY_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}


def check_corrosion_category(system, required):
    if required is None:
        return True, "Категория коррозии не задана — проверка пропущена"
    sys_cats = [_cat_value(c) for c in system.corrosion_categories]
    req = _cat_value(required)
    if not sys_cats:
        return False, f"Недостаточно данных: в системе не указаны категории коррозии (требуется {req})"
    if req in sys_cats:
        return True, f"Соответствует категории {req}"
    return False, f"Система не покрывает категорию {req} (есть: {', '.join(sys_cats)})"


def check_durability(system, required):
    if required is None:
        return True, "Долговечность не задана — проверка пропущена"
    if system.durability is None:
        return False, f"Недостаточно данных: в системе не указана долговечность (требуется {_dur_value(required)})"
    sys_level = DURABILITY_ORDER.get(_dur_value(system.durability), 0)
    req_level = DURABILITY_ORDER.get(_dur_value(required), 0)
    if sys_level >= req_level:
        return True, f"Долговечность {_dur_value(system.durability)} ≥ {_dur_value(required)}"
    return False, f"Долговечность {_dur_value(system.durability)} < требуемой {_dur_value(required)}"


def check_surface(system, required):
    if required is None:
        return True, "Тип поверхности не задан — проверка пропущена"
    sys_surfaces = [s.value if hasattr(s, "value") else str(s) for s in system.surface_types]
    req = required.value if hasattr(required, "value") else str(required)
    if not sys_surfaces:
        return False, f"Недостаточно данных: тип поверхности в системе не указан (запрошен: {req})"
    if req in sys_surfaces:
        return True, f"Подходит для поверхности «{req}»"
    return False, f"Система не предназначена для «{req}» (есть: {', '.join(sys_surfaces)})"


def check_environment(system, required):
    if required is None:
        return True, "Тип среды не задан — проверка пропущена"
    sys_envs = [e.value if hasattr(e, "value") else str(e) for e in system.environments]
    req = required.value if hasattr(required, "value") else str(required)
    if not sys_envs:
        return False, f"Недостаточно данных: среда в системе не указана (запрошена: {req})"
    if req in sys_envs:
        return True, f"Подходит для среды «{req}»"
    return False, f"Система не для среды «{req}» (есть: {', '.join(sys_envs)})"


def check_temperature(system, t_min, t_max):
    if t_min is None and t_max is None:
        return True, "Температура не задана — проверка пропущена"
    sys_min, sys_max = system.temperature_min, system.temperature_max
    if sys_min is None and sys_max is None:
        return False, "Недостаточно данных: температурный диапазон системы не указан"
    messages = []
    if t_min is not None:
        if sys_min is None:
            return False, "Недостаточно данных: нижняя граница температуры системы не указана"
        if t_min < sys_min:
            messages.append(f"Требуемый минимум {t_min} °C ниже допустимого {sys_min} °C")
    if t_max is not None:
        if sys_max is None:
            return False, "Недостаточно данных: верхняя граница температуры системы не указана"
        if t_max > sys_max:
            messages.append(f"Требуемый максимум {t_max} °C выше допустимого {sys_max} °C")
    if messages:
        return False, "; ".join(messages)
    return True, f"Температурный диапазон системы: {sys_min}…{sys_max} °C"


def check_has_layers(system):
    if not system.layers:
        return False, "Система не содержит слоёв"
    return True, f"Слоёв: {len(system.layers)}"


def _add_technology_checks(result: FilterResult, obj: ObjectData) -> None:
    for layer in result.system.layers:
        material = layer.material
        if material is None:
            result.passed = False
            result.reasons_fail.append(f"Слой {layer.layer_number}: материал не загружен")
            result.insufficient_data = True
            continue
        tech = check_application_technology(obj, material, actual_dft=None)
        for issue in tech.issues:
            if issue.level == "error":
                result.passed = False
                result.reasons_fail.append(f"Слой {layer.layer_number}: {issue.message}")
            else:
                result.notes.append(f"Слой {layer.layer_number}: {issue.message}")
        target = check_target_dft(material, layer.target_dft)
        for issue in target.issues:
            if issue.level == "error":
                result.passed = False
                result.reasons_fail.append(f"Слой {layer.layer_number}: {issue.message}")
            elif issue.level == "warning":
                result.notes.append(f"Слой {layer.layer_number}: {issue.message}")

        if obj.application_method is not None and material.application_method is not None:
            obj_method = obj.application_method.value if hasattr(obj.application_method, "value") else str(obj.application_method)
            mat_method = material.application_method.value if hasattr(material.application_method, "value") else str(material.application_method)
            if obj_method != mat_method:
                result.passed = False
                result.reasons_fail.append(f"Слой {layer.layer_number}: способ нанесения объекта «{obj_method}» не соответствует материалу «{mat_method}»")


def filter_system(system, obj, require_corrosion=True, require_durability=True):
    result = FilterResult(system=system, passed=True)
    checks = [
        ("corrosion", check_corrosion_category(system, obj.corrosion_category)),
        ("durability", check_durability(system, obj.durability)),
        ("surface", check_surface(system, obj.surface_type)),
        ("environment", check_environment(system, obj.environment)),
        ("temperature", check_temperature(system, obj.temperature_min, obj.temperature_max)),
        ("layers", check_has_layers(system)),
    ]
    for kind, (ok, msg) in checks:
        if ok:
            result.reasons_pass.append(msg)
            continue
        result.passed = False
        result.reasons_fail.append(msg)
        if "Недостаточно данных" in msg:
            result.insufficient_data = True

    if not require_corrosion and obj.corrosion_category is not None and not system.corrosion_categories:
        result.insufficient_data = False
    if not require_durability and obj.durability is not None and system.durability is None:
        result.insufficient_data = False

    _add_technology_checks(result, obj)
    return result


def filter_systems(systems: Sequence, obj: ObjectData, require_corrosion=True, require_durability=True):
    return [filter_system(s, obj, require_corrosion=require_corrosion, require_durability=require_durability) for s in systems]
