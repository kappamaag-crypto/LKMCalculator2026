"""
Ранжирование (scoring) систем, прошедших фильтр.

Score 0–100. Веса настраиваемые.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import CoatingSystem, ObjectData, SystemCalculationResult
from app.domain.recommendation.rules import FilterResult, DURABILITY_ORDER, _cat_value, _dur_value


@dataclass
class ScoreWeights:
    """Весовые коэффициенты (сумма ≈ 1.0)."""

    conditions: float = 0.30      # общее соответствие условиям
    corrosion: float = 0.20
    durability: float = 0.15
    temperature: float = 0.10
    compatibility: float = 0.10
    technology: float = 0.05      # меньше слоёв — чуть лучше
    cost: float = 0.10

    def normalized(self) -> "ScoreWeights":
        total = (
            self.conditions + self.corrosion + self.durability
            + self.temperature + self.compatibility + self.technology + self.cost
        )
        if total <= 0:
            return self
        return ScoreWeights(
            conditions=self.conditions / total,
            corrosion=self.corrosion / total,
            durability=self.durability / total,
            temperature=self.temperature / total,
            compatibility=self.compatibility / total,
            technology=self.technology / total,
            cost=self.cost / total,
        )


@dataclass
class ScoreBreakdown:
    """Детализация баллов."""

    conditions: float = 0.0
    corrosion: float = 0.0
    durability: float = 0.0
    temperature: float = 0.0
    compatibility: float = 0.0
    technology: float = 0.0
    cost: float = 0.0
    total: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _score_corrosion(system: CoatingSystem, obj: ObjectData) -> tuple[float, str]:
    """0–100 за категорию коррозии."""
    if obj.corrosion_category is None:
        return 70.0, "Категория коррозии не задана пользователем"

    req = _cat_value(obj.corrosion_category)
    sys_cats = [_cat_value(c) for c in system.corrosion_categories]

    if not sys_cats:
        return 30.0, "Категория коррозии системы не указана"

    if req in sys_cats:
        return 100.0, f"Точное соответствие категории {req}"

    return 0.0, f"Категория {req} не покрывается"


def _score_durability(system: CoatingSystem, obj: ObjectData) -> tuple[float, str]:
    if obj.durability is None:
        return 70.0, "Долговечность не задана пользователем"

    if system.durability is None:
        return 30.0, "Долговечность системы не указана"

    sys_l = DURABILITY_ORDER.get(_dur_value(system.durability), 0)
    req_l = DURABILITY_ORDER.get(_dur_value(obj.durability), 0)

    if sys_l >= req_l:
        # Бонус за запас
        bonus = min(20.0, (sys_l - req_l) * 10.0)
        return 80.0 + bonus, f"Долговечность {_dur_value(system.durability)} ≥ {_dur_value(obj.durability)}"

    return 0.0, f"Долговечность недостаточна"


def _score_temperature(system: CoatingSystem, obj: ObjectData) -> tuple[float, str]:
    if obj.temperature_min is None and obj.temperature_max is None:
        return 70.0, "Температура не задана"

    if system.temperature_min is None and system.temperature_max is None:
        return 40.0, "Температурный диапазон системы не указан"

    ok = True
    if obj.temperature_min is not None and system.temperature_min is not None:
        if obj.temperature_min < system.temperature_min:
            ok = False
    if obj.temperature_max is not None and system.temperature_max is not None:
        if obj.temperature_max > system.temperature_max:
            ok = False

    if ok:
        return 100.0, "Температурный диапазон подходит"
    return 0.0, "Температура вне диапазона системы"


def _score_conditions(filter_result: FilterResult) -> tuple[float, str]:
    """Общее соответствие по результатам фильтра."""
    if not filter_result.passed:
        return 0.0, "Не прошла фильтр"
    n_pass = len(filter_result.reasons_pass)
    n_fail = len(filter_result.reasons_fail)
    total = n_pass + n_fail
    if total == 0:
        return 50.0, "Нет данных для оценки"
    score = 100.0 * n_pass / total
    return score, f"Пройдено проверок: {n_pass}/{total}"


def _score_technology(system: CoatingSystem) -> tuple[float, str]:
    """Меньше слоёв — чуть технологичнее (при прочих равных)."""
    n = len(system.layers) if system.layers else system.number_of_layers or 0
    if n <= 0:
        return 40.0, "Количество слоёв неизвестно"
    if n == 1:
        return 100.0, "Однослойная система"
    if n == 2:
        return 90.0, "Двухслойная система"
    if n == 3:
        return 75.0, "Трёхслойная система"
    return max(40.0, 100.0 - n * 15), f"Слоёв: {n}"


def _score_cost(
    calc: Optional[SystemCalculationResult],
    all_costs: Sequence[float],
) -> tuple[float, str]:
    """Чем дешевле относительно других — тем выше балл."""
    if calc is None or not all_costs:
        return 50.0, "Стоимость не рассчитана"

    cost = calc.total_cost_per_m2
    min_c = min(all_costs)
    max_c = max(all_costs)

    if max_c <= min_c:
        return 80.0, f"Стоимость {cost:.1f} руб/м²"

    # 100 для самой дешёвой, 0 для самой дорогой
    score = 100.0 * (max_c - cost) / (max_c - min_c)
    return score, f"Стоимость {cost:.1f} руб/м² (мин {min_c:.1f}, макс {max_c:.1f})"


def _score_compatibility(system: CoatingSystem, compatibility_ok: bool = True) -> tuple[float, str]:
    if not system.layers or len(system.layers) < 2:
        return 80.0, "Один слой — проверка совместимости не требуется"
    if compatibility_ok:
        return 100.0, "Совместимость слоёв подтверждена / не противоречит"
    return 40.0, "Есть предупреждения по совместимости слоёв"


def score_system(
    filter_result: FilterResult,
    obj: ObjectData,
    calc_result: Optional[SystemCalculationResult] = None,
    all_costs: Optional[Sequence[float]] = None,
    weights: Optional[ScoreWeights] = None,
    compatibility_ok: bool = True,
) -> ScoreBreakdown:
    """
    Рассчитать Score 0–100 для системы, прошедшей фильтр.
    """
    w = (weights or ScoreWeights()).normalized()
    br = ScoreBreakdown()

    c_cond, r_cond = _score_conditions(filter_result)
    c_corr, r_corr = _score_corrosion(filter_result.system, obj)
    c_dur, r_dur = _score_durability(filter_result.system, obj)
    c_temp, r_temp = _score_temperature(filter_result.system, obj)
    c_tech, r_tech = _score_technology(filter_result.system)
    c_cost, r_cost = _score_cost(calc_result, all_costs or [])
    c_comp, r_comp = _score_compatibility(filter_result.system, compatibility_ok)

    br.conditions = c_cond
    br.corrosion = c_corr
    br.durability = c_dur
    br.temperature = c_temp
    br.technology = c_tech
    br.cost = c_cost
    br.compatibility = c_comp

    br.total = round(
        w.conditions * c_cond
        + w.corrosion * c_corr
        + w.durability * c_dur
        + w.temperature * c_temp
        + w.compatibility * c_comp
        + w.technology * c_tech
        + w.cost * c_cost,
        1,
    )

    # Причины (положительные)
    for score_val, reason in [
        (c_corr, r_corr), (c_dur, r_dur), (c_temp, r_temp),
        (c_tech, r_tech), (c_comp, r_comp),
    ]:
        if score_val >= 70:
            br.reasons.append(reason)
        elif score_val < 40:
            br.warnings.append(reason)

    if calc_result:
        br.reasons.append(r_cost)

    # Ограничения
    br.limitations.append(
        "Предварительный подбор. Окончательный выбор — по TDS производителя и проектным требованиям."
    )
    if filter_result.insufficient_data:
        br.limitations.append("Недостаточно данных в карточке системы для полной оценки.")
    if filter_result.notes:
        br.warnings.extend(filter_result.notes)

    return br