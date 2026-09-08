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
    conditions: float = 0.30
    corrosion: float = 0.20
    durability: float = 0.15
    temperature: float = 0.10
    compatibility: float = 0.10
    technology: float = 0.05
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
    if obj.corrosion_category is None:
        return 70.0, "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u043c"
    req = _cat_value(obj.corrosion_category)
    sys_cats = [_cat_value(c) for c in system.corrosion_categories]
    if not sys_cats:
        return 30.0, "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f \u043a\u043e\u0440\u0440\u043e\u0437\u0438\u0438 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430"
    if req in sys_cats:
        return 100.0, f"\u0422\u043e\u0447\u043d\u043e\u0435 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 {req}"
    return 0.0, f"\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f {req} \u043d\u0435 \u043f\u043e\u043a\u0440\u044b\u0432\u0430\u0435\u0442\u0441\u044f"


def _score_durability(system: CoatingSystem, obj: ObjectData) -> tuple[float, str]:
    if obj.durability is None:
        return 70.0, "\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u043c"
    if system.durability is None:
        return 30.0, "\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430"
    sys_l = DURABILITY_ORDER.get(_dur_value(system.durability), 0)
    req_l = DURABILITY_ORDER.get(_dur_value(obj.durability), 0)
    if sys_l >= req_l:
        bonus = min(20.0, (sys_l - req_l) * 10.0)
        return 80.0 + bonus, f"\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c {_dur_value(system.durability)} \u2265 {_dur_value(obj.durability)}"
    return 0.0, "\u0414\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u043e\u0441\u0442\u044c \u043d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u0430"


def _score_temperature(system: CoatingSystem, obj: ObjectData) -> tuple[float, str]:
    if obj.temperature_min is None and obj.temperature_max is None:
        return 70.0, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d\u0430"
    if system.temperature_min is None and system.temperature_max is None:
        return 40.0, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u043d\u044b\u0439 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d"
    ok = True
    if obj.temperature_min is not None and system.temperature_min is not None:
        if obj.temperature_min < system.temperature_min:
            ok = False
    if obj.temperature_max is not None and system.temperature_max is not None:
        if obj.temperature_max > system.temperature_max:
            ok = False
    if ok:
        return 100.0, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u043d\u044b\u0439 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d \u043f\u043e\u0434\u0445\u043e\u0434\u0438\u0442"
    return 0.0, "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u0432\u043d\u0435 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0430 \u0441\u0438\u0441\u0442\u0435\u043c\u044b"


def _score_conditions(filter_result: FilterResult) -> tuple[float, str]:
    if not filter_result.passed:
        return 0.0, "\u041d\u0435 \u043f\u0440\u043e\u0448\u043b\u0430 \u0444\u0438\u043b\u044c\u0442\u0440"
    n_pass = len(filter_result.reasons_pass)
    n_fail = len(filter_result.reasons_fail)
    total = n_pass + n_fail
    if total == 0:
        return 50.0, "\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 \u0434\u043b\u044f \u043e\u0446\u0435\u043d\u043a\u0438"
    score = 100.0 * n_pass / total
    return score, f"\u041f\u0440\u043e\u0439\u0434\u0435\u043d\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u043e\u043a: {n_pass}/{total}"


def _score_technology(system: CoatingSystem) -> tuple[float, str]:
    n = len(system.layers) if system.layers else system.number_of_layers or 0
    if n <= 0:
        return 40.0, "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0441\u043b\u043e\u0451\u0432 \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e"
    if n == 1:
        return 100.0, "\u041e\u0434\u043d\u043e\u0441\u043b\u043e\u0439\u043d\u0430\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u0430"
    if n == 2:
        return 90.0, "\u0414\u0432\u0443\u0445\u0441\u043b\u043e\u0439\u043d\u0430\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u0430"
    if n == 3:
        return 75.0, "\u0422\u0440\u0451\u0445\u0441\u043b\u043e\u0439\u043d\u0430\u044f \u0441\u0438\u0441\u0442\u0435\u043c\u0430"
    return max(40.0, 100.0 - n * 15), f"\u0421\u043b\u043e\u0451\u0432: {n}"


def _score_cost(
    calc: Optional[SystemCalculationResult],
    all_costs: Sequence[float],
) -> tuple[float, str]:
    if calc is None or not all_costs:
        return 50.0, "\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043d\u0435 \u0440\u0430\u0441\u0441\u0447\u0438\u0442\u0430\u043d\u0430"
    cost = calc.total_cost_per_m2
    min_c = min(all_costs)
    max_c = max(all_costs)
    if max_c <= min_c:
        return 80.0, f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c {cost:.1f} \u0440\u0443\u0431/\u043c\u00b2"
    score = 100.0 * (max_c - cost) / (max_c - min_c)
    return score, f"\u0421\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c {cost:.1f} \u0440\u0443\u0431/\u043c\u00b2 (\u043c\u0438\u043d {min_c:.1f}, \u043c\u0430\u043a\u0441 {max_c:.1f})"


def _score_compatibility(system: CoatingSystem, compatibility_ok: bool = True) -> tuple[float, str]:
    if not system.layers or len(system.layers) < 2:
        return 80.0, "\u041e\u0434\u0438\u043d \u0441\u043b\u043e\u0439 \u2014 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u0438 \u043d\u0435 \u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f"
    if compatibility_ok:
        return 100.0, "\u0421\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u044c \u0441\u043b\u043e\u0451\u0432 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0430 / \u043d\u0435 \u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0440\u0435\u0447\u0438\u0442"
    return 40.0, "\u0415\u0441\u0442\u044c \u043f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f \u043f\u043e \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u0438 \u0441\u043b\u043e\u0451\u0432"


def score_system(
    filter_result: FilterResult,
    obj: ObjectData,
    calc_result: Optional[SystemCalculationResult] = None,
    all_costs: Optional[Sequence[float]] = None,
    weights: Optional[ScoreWeights] = None,
    compatibility_ok: bool = True,
) -> ScoreBreakdown:
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

    br.limitations.append(
        "\u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043f\u043e\u0434\u0431\u043e\u0440. \u041e\u043a\u043e\u043d\u0447\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0432\u044b\u0431\u043e\u0440 \u2014 \u043f\u043e TDS \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f \u0438 \u043f\u0440\u043e\u0435\u043a\u0442\u043d\u044b\u043c \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f\u043c."
    )
    if filter_result.insufficient_data:
        br.limitations.append("\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0434\u0430\u043d\u043d\u044b\u0445 \u0432 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u044b \u0434\u043b\u044f \u043f\u043e\u043b\u043d\u043e\u0439 \u043e\u0446\u0435\u043d\u043a\u0438.")
    if filter_result.notes:
        br.warnings.extend(filter_result.notes)

    return br
