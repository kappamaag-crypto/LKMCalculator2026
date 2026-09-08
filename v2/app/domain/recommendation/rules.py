"""
Правила фильтрации систем АКЗ (этап 1 рекомендаций).

Жёсткий фильтр: система либо проходит, либо отсеивается.
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


DURABILITY_ORDER = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Very High": 4,
}


def check_corrosion_category(system: CoatingSystem, required: Optional[CorrosionCategory]) -> tuple[bool, str]:
    if required is None:
        return True, "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430 \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
    sys_cats = [_cat_value(c) for c in system.corrosion_categories]
    req = _cat_value(required)
    if not sys_cats:
        return False, f"\u0412 \u0441\u0438\u0441\u0442\u0435\u043c\u0435 \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u044b \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 (\u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f {req})"
    if req in sys_cats:
        return True, f"\u0421\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 {req}"
    return False, f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0435 \u043f\u043e\u043a\u0440\u044b\u0432\u0430\u0435\u0442 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044e {req} (\u0435\u0441\u0442\u044c: {', '.join(sys_cats)})"


def check_durability(system: CoatingSystem, required: Optional[DurabilityLevel]) -> tuple[bool, str]:
    if required is None:
        return True, "\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430 \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
    if system.durability is None:
        return False, f"\u0412 \u0441\u0438\u0441\u0442\u0435\u043c\u0435 \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430 \u0434\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c (\u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f {_dur_value(required)})"
    sys_level = DURABILITY_ORDER.get(_dur_value(system.durability), 0)
    req_level = DURABILITY_ORDER.get(_dur_value(required), 0)
    if sys_level >= req_level:
        return True, f"\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c {_dur_value(system.durability)} \u2265 {_dur_value(required)}"
    return False, f"\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c {_dur_value(system.durability)} < \u0442\u0440\u0435\u0431\u0443\u0435\u043c\u043e\u0439 {_dur_value(required)}"


def check_surface(system: CoatingSystem, required: Optional[SurfaceType]) -> tuple[bool, str]:
    if required is None:
        return True, "\u0422\u0438\u043f \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
    sys_surfaces = [s.value if hasattr(s, "value") else str(s) for s in system.surface_types]
    req = required.value if hasattr(required, "value") else str(required)
    if not sys_surfaces:
        return True, f"\u0422\u0438\u043f \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438 \u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0435 \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d (\u0437\u0430\u043f\u0440\u043e\u0448\u0435\u043d: {req})"
    if req in sys_surfaces:
        return True, f"\u041f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u0434\u043b\u044f \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438 \u00ab{req}\u00bb"
    return False, f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0435 \u043f\u0440\u0435\u0434\u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0430 \u0434\u043b\u044f \u00ab{req}\u00bb (\u0435\u0441\u0442\u044c: {', '.join(sys_surfaces)})"


def check_environment(system: CoatingSystem, required: Optional[EnvironmentType]) -> tuple[bool, str]:
    if required is None:
        return True, "\u0422\u0438\u043f \u0441\u0440\u0435\u0434\u044b \u043d\u0435 \u0437\u0430\u0434\u0430\u043d \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
    sys_envs = [e.value if hasattr(e, "value") else str(e) for e in system.environments]
    req = required.value if hasattr(required, "value") else str(required)
    if not sys_envs:
        return True, f"\u0421\u0440\u0435\u0434\u0430 \u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0435 \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430 (\u0437\u0430\u043f\u0440\u043e\u0448\u0435\u043d\u0430: {req})"
    if req in sys_envs:
        return True, f"\u041f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u0434\u043b\u044f \u0441\u0440\u0435\u0434\u044b \u00ab{req}\u00bb"
    return False, f"\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0435 \u0434\u043b\u044f \u0441\u0440\u0435\u0434\u044b \u00ab{req}\u00bb (\u0435\u0441\u0442\u044c: {', '.join(sys_envs)})"


def check_temperature(
    system: CoatingSystem,
    t_min: Optional[float],
    t_max: Optional[float],
) -> tuple[bool, str]:
    if t_min is None and t_max is None:
        return True, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430 \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043f\u0440\u043e\u043f\u0443\u0449\u0435\u043d\u0430"
    sys_min = system.temperature_min
    sys_max = system.temperature_max
    if sys_min is None and sys_max is None:
        return True, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u043d\u044b\u0439 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d"
    messages = []
    ok = True
    if t_min is not None and sys_min is not None and t_min < sys_min:
        ok = False
        messages.append(f"\u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043c\u0438\u043d\u0438\u043c\u0443\u043c {t_min} \u00b0C \u043d\u0438\u0436\u0435 \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u043e\u0433\u043e {sys_min} \u00b0C")
    if t_max is not None and sys_max is not None and t_max > sys_max:
        ok = False
        messages.append(f"\u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c {t_max} \u00b0C \u0432\u044b\u0448\u0435 \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u043e\u0433\u043e {sys_max} \u00b0C")
    if ok:
        range_str = f"{sys_min or '\u2014'}\u2026{sys_max or '\u2014'} \u00b0C"
        return True, f"\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u043d\u044b\u0439 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d \u0441\u0438\u0441\u0442\u0435\u043c\u044b: {range_str}"
    return False, "; ".join(messages)


def check_has_layers(system: CoatingSystem) -> tuple[bool, str]:
    if not system.layers:
        return False, "\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0435 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 \u0441\u043b\u043e\u0451\u0432"
    return True, f"\u0421\u043b\u043e\u0451\u0432: {len(system.layers)}"


def filter_system(
    system: CoatingSystem,
    obj: ObjectData,
    require_corrosion: bool = True,
    require_durability: bool = True,
) -> FilterResult:
    result = FilterResult(system=system, passed=True)
    checks = [
        check_has_layers(system),
        check_corrosion_category(system, obj.corrosion_category),
        check_durability(system, obj.durability),
        check_surface(system, obj.surface_type),
        check_environment(system, obj.environment),
        check_temperature(system, obj.temperature_min, obj.temperature_max),
    ]
    if obj.corrosion_category and not system.corrosion_categories:
        if require_corrosion:
            result.passed = False
            result.reasons_fail.append(
                f"\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0434\u0430\u043d\u043d\u044b\u0445: \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430 (\u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f {_cat_value(obj.corrosion_category)})"
            )
            result.insufficient_data = True
        else:
            result.notes.append("\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430")
    if obj.durability and system.durability is None:
        if require_durability:
            result.passed = False
            result.reasons_fail.append(
                f"\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0434\u0430\u043d\u043d\u044b\u0445: \u0434\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430 (\u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f {_dur_value(obj.durability)})"
            )
            result.insufficient_data = True
        else:
            result.notes.append("\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430")
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
    return [
        filter_system(s, obj, require_corrosion=require_corrosion, require_durability=require_durability)
        for s in systems
    ]
