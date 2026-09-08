"""
Правила фильтрации систем АКЗ (этап 1 рекомендаций).

Жёсткий фильтр: система либо проходит, либо отсеивается.
Не делаем предположений — при отсутствии данных в базе
система получает пометку «недостаточно данных».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import CoatingSystem, ObjectData, Material
from app.domain.enums import (
    CorrosionCategory,
    DurabilityLevel,
    SurfaceType,
    EnvironmentType,
    CompatibilityStatus,
)


@dataclass
class FilterResult:
    """Результат фильтрации одной системы."""

    system: CoatingSystem
    passed: bool
    reasons_pass: list[str] = field(default_factory=list)
    reasons_fail: list[str] = field(default_factory=list)
    insufficient_data: bool = False
    notes: list[str] = field(default_factory=list)


def _cat_value(cat) -> str:
    if cat is None:
        return ""
    return cat.value if hasattr(cat, "value") else str(cat)


def _dur_value(dur) -> str:
    if dur is None:
        return ""
    return dur.value if hasattr(dur, "value") else str(dur)


# Порядок долговечности для сравнения
DURABILITY_ORDER = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Very High": 4,
}


def check_corrosion_category(system: CoatingSystem, required: Optional[CorrosionCategory]) -> tuple[bool, str]:
    """Проверка категории коррозии."""
    if required is None:
        return True, "Категория коррозии не задана — проверка пропущена"

    sys_cats = [_cat_value(c) for c in system.corrosion_categories]
    req = _cat_value(required)

    if not sys_cats:
        return False, f"В системе не указаны категории коррозии (требуется {req})"

    if req in sys_cats:
        return True, f"Соответствует категории {req}"

    return False, f"Система не покрывает категорию {req} (есть: {', '.join(sys_cats)})"


def check_durability(system: CoatingSystem, required: Optional[DurabilityLevel]) -> tuple[bool, str]:
    """Проверка долговечности (система должна быть >= требуемой)."""
    if required is None:
        return True, "Долговечность не задана — проверка пропущена"

    if system.durability is None:
        return False, f"В системе не указана долговечность (требуется {_dur_value(required)})"

    sys_level = DURABILITY_ORDER.get(_dur_value(system.durability), 0)
    req_level = DURABILITY_ORDER.get(_dur_value(required), 0)

    if sys_level >= req_level:
        return True, f"Долговечность {_dur_value(system.durability)} ≥ {_dur_value(required)}"

    return False, f"Долговечность {_dur_value(system.durability)} < требуемой {_dur_value(required)}"


def check_surface(system: CoatingSystem, required: Optional[SurfaceType]) -> tuple[bool, str]:
    """Проверка типа поверхности / основания."""
    if required is None:
        return True, "Тип поверхности не задан — проверка пропущена"

    sys_surfaces = [
        s.value if hasattr(s, "value") else str(s)
        for s in system.surface_types
    ]
    req = required.value if hasattr(required, "value") else str(required)

    if not sys_surfaces:
        # Нет данных — не отсеиваем жёстко, но помечаем
        return True, f"Тип поверхности в системе не указан (запрошен: {req})"

    if req in sys_surfaces:
        return True, f"Подходит для поверхности «{req}»"

    return False, f"Система не предназначена для «{req}» (есть: {', '.join(sys_surfaces)})"


def check_environment(system: CoatingSystem, required: Optional[EnvironmentType]) -> tuple[bool, str]:
    """Проверка типа среды."""
    if required is None:
        return True, "Тип среды не задан — проверка пропущена"

    sys_envs = [
        e.value if hasattr(e, "value") else str(e)
        for e in system.environments
    ]
    req = required.value if hasattr(required, "value") else str(required)

    if not sys_envs:
        return True, f"Среда в системе не указана (запрошена: {req})"

    if req in sys_envs:
        return True, f"Подходит для среды «{req}»"

    return False, f"Система не для среды «{req}» (есть: {', '.join(sys_envs)})"


def check_temperature(
    system: CoatingSystem,
    t_min: Optional[float],
    t_max: Optional[float],
) -> tuple[bool, str]:
    """Проверка температурного диапазона эксплуатации."""
    if t_min is None and t_max is None:
        return True, "Температура не задана — проверка пропущена"

    sys_min = system.temperature_min
    sys_max = system.temperature_max

    if sys_min is None and sys_max is None:
        return True, "Температурный диапазон системы не указан"

    messages = []
    ok = True

    if t_min is not None and sys_min is not None and t_min < sys_min:
        ok = False
        messages.append(f"Требуемый минимум {t_min} °C ниже допустимого {sys_min} °C")
    if t_max is not None and sys_max is not None and t_max > sys_max:
        ok = False
        messages.append(f"Требуемый максимум {t_max} °C выше допустимого {sys_max} °C")

    if ok:
        range_str = f"{sys_min or '—'}…{sys_max or '—'} °C"
        return True, f"Температурный диапазон системы: {range_str}"

    return False, "; ".join(messages)


def check_has_layers(system: CoatingSystem) -> tuple[bool, str]:
    """Система должна содержать хотя бы один слой."""
    if not system.layers:
        return False, "Система не содержит слоёв"
    return True, f"Слоёв: {len(system.layers)}"


def filter_system(
    system: CoatingSystem,
    obj: ObjectData,
    require_corrosion: bool = True,
    require_durability: bool = True,
) -> FilterResult:
    """
    Жёсткий фильтр одной системы по условиям объекта.

    require_* — если True и данных нет, система не проходит.
    """
    result = FilterResult(system=system, passed=True)

    checks = [
        check_has_layers(system),
        check_corrosion_category(system, obj.corrosion_category),
        check_durability(system, obj.durability),
        check_surface(system, obj.surface_type),
        check_environment(system, obj.environment),
        check_temperature(system, obj.temperature_min, obj.temperature_max),
    ]

    # Особые случаи «нет данных»
    if obj.corrosion_category and not system.corrosion_categories:
        if require_corrosion:
            result.passed = False
            result.reasons_fail.append(
                f"Недостаточно данных: категория коррозии системы не указана (требуется {_cat_value(obj.corrosion_category)})"
            )
            result.insufficient_data = True
        else:
            result.notes.append("Категория коррозии системы не указана")

    if obj.durability and system.durability is None:
        if require_durability:
            result.passed = False
            result.reasons_fail.append(
                f"Недостаточно данных: долговечность системы не указана (требуется {_dur_value(obj.durability)})"
            )
            result.insufficient_data = True
        else:
            result.notes.append("Долговечность системы не указана")

    for ok, msg in checks:
        if ok:
            result.reasons_pass.append(msg)
        else:
            result.passed = False
            result.reasons_fail.append(msg)

    return result


def filter_systems(
    systems: Sequence[CoatingSystem],
    obj: ObjectData,
    require_corrosion: bool = True,
    require_durability: bool = True,
) -> list[FilterResult]:
    """Отфильтровать список систем."""
    return [
        filter_system(s, obj, require_corrosion=require_corrosion, require_durability=require_durability)
        for s in systems
    ]