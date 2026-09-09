"""Простое ранжирование систем, уже прошедших hard-filter."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence
from app.domain.models import CoatingSystem, ObjectData, SystemCalculationResult
from app.domain.recommendation.rules import FilterResult, DURABILITY_ORDER, _cat_value, _dur_value

@dataclass
class ScoreWeights:
    """Понятные веса для мягкого ранжирования допустимых систем."""
    corrosion: float = 0.30
    durability: float = 0.25
    technology: float = 0.20
    cost: float = 0.25
    def normalized(self) -> "ScoreWeights":
        total = self.corrosion + self.durability + self.technology + self.cost
        if total <= 0: return self
        return ScoreWeights(self.corrosion/total, self.durability/total, self.technology/total, self.cost/total)

@dataclass
class ScoreBreakdown:
    corrosion: float = 0.0; durability: float = 0.0; temperature: float = 0.0
    compatibility: float = 0.0; technology: float = 0.0; conditions: float = 0.0
    cost: float = 0.0; total: float = 0.0; status: str = ""
    reasons: list[str] = field(default_factory=list); warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

def recommendation_status(filter_result: FilterResult) -> str:
    if not filter_result.passed:
        return "Недостаточно данных" if filter_result.insufficient_data else "Не подходит"
    return "Недостаточно данных" if filter_result.insufficient_data else "Подходит"

def _score_corrosion(system: CoatingSystem, obj: ObjectData) -> tuple[float,str]:
    if obj.corrosion_category is None: return 50.0, "Категория коррозии не задана"
    req = _cat_value(obj.corrosion_category); cats = [_cat_value(c) for c in system.corrosion_categories]
    return (100.0, f"Соответствует категории {req}") if req in cats else (0.0, f"Категория {req} не покрывается")

def _score_durability(system: CoatingSystem, obj: ObjectData) -> tuple[float,str]:
    if obj.durability is None or system.durability is None: return 50.0, "Долговечность недостаточно определена для дополнительного ранжирования"
    sys_l = DURABILITY_ORDER.get(_dur_value(system.durability),0); req_l = DURABILITY_ORDER.get(_dur_value(obj.durability),0)
    return min(100.0, 75.0 + max(0,sys_l-req_l)*25.0), f"Долговечность {_dur_value(system.durability)}"

def _score_technology(system: CoatingSystem) -> tuple[float,str]:
    n = len(system.layers) if system.layers else system.number_of_layers or 0
    return (50.0, "Количество слоёв не указано") if n <= 0 else (max(50.0,100.0-(n-1)*15.0), f"Слоёв: {n}")

def _score_cost(calc: Optional[SystemCalculationResult], all_costs: Sequence[float]) -> tuple[float,str]:
    if calc is None or calc.total_cost_per_m2 is None: return 50.0, "Стоимость не рассчитана"
    if not all_costs: return 50.0, f"Стоимость {calc.total_cost_per_m2:.1f} руб/м²"
    low, high = min(all_costs), max(all_costs)
    if high == low: return 100.0, f"Стоимость {calc.total_cost_per_m2:.1f} руб/м²"
    return 100.0*(high-calc.total_cost_per_m2)/(high-low), f"Стоимость {calc.total_cost_per_m2:.1f} руб/м²"

def score_system(filter_result: FilterResult, obj: ObjectData, calc_result: Optional[SystemCalculationResult]=None, all_costs: Optional[Sequence[float]]=None, weights: Optional[ScoreWeights]=None, compatibility_ok: bool=True) -> ScoreBreakdown:
    """Score применяется только после hard-filter и использует четыре прозрачных фактора."""
    w=(weights or ScoreWeights()).normalized(); br=ScoreBreakdown(status=recommendation_status(filter_result))
    corr, rc=_score_corrosion(filter_result.system,obj); dur, rd=_score_durability(filter_result.system,obj); tech, rt=_score_technology(filter_result.system); cost, rcost=_score_cost(calc_result,all_costs or [])
    br.corrosion,br.durability,br.technology,br.cost=corr,dur,tech,cost
    br.total=0.0 if not filter_result.passed else w.corrosion*corr+w.durability*dur+w.technology*tech+w.cost*cost
    if corr>=70: br.reasons.append(rc)
    if dur>=70: br.reasons.append(rd)
    if tech>=70: br.reasons.append(rt)
    if calc_result: br.reasons.append(rcost)
    if filter_result.reasons_fail: br.warnings.extend(filter_result.reasons_fail)
    if filter_result.notes: br.warnings.extend(filter_result.notes)
    br.limitations.append("Предварительный подбор; окончательный выбор — по TDS производителя и проектным требованиям.")
    if filter_result.insufficient_data: br.limitations.append("Часть данных отсутствует, поэтому Score не заменяет инженерную проверку.")
    return br
