"""Прозрачное сравнение систем покрытия."""
from __future__ import annotations
from datetime import datetime
from typing import Sequence
from app.domain.models import ObjectData, SystemCalculationResult, ComparisonResult
from app.domain.calculator import SystemCalculator, LayerInput

class ComparisonEngine:
    """Сравнение 2–10 систем без производных «умных» рейтингов."""
    def __init__(self, calculator: SystemCalculator | None = None): self.calculator = calculator or SystemCalculator()
    def compare(self,obj:ObjectData,systems:Sequence[tuple[str,Sequence[LayerInput]]])->ComparisonResult:
        if len(systems)<2: raise ValueError("Для сравнения требуется не менее 2 систем")
        if len(systems)>10: raise ValueError("Максимум 10 систем для сравнения")
        from app.domain.models import CoatingSystem
        results=[]
        for name,layers in systems:
            result,_=self.calculator.calculate(obj,layers,system=CoatingSystem(system_name=name)); results.append(result)
        comparison=ComparisonResult(object_data=obj,systems=results,created_at=datetime.now()); self._annotate(comparison); return comparison
    def compare_results(self,obj:ObjectData,results:Sequence[SystemCalculationResult])->ComparisonResult:
        if len(results)<2: raise ValueError("Для сравнения требуется не менее 2 систем")
        comparison=ComparisonResult(object_data=obj,systems=list(results),created_at=datetime.now()); self._annotate(comparison); return comparison
    def _annotate(self,comparison:ComparisonResult)->None:
        systems=comparison.systems
        if not systems: return
        known=[(i,s.total_cost_per_m2) for i,s in enumerate(systems) if s.total_cost_per_m2 is not None]
        comparison.cheapest_index=min(known,key=lambda x:x[1])[0] if known else None
        comparison.most_expensive_index=max(known,key=lambda x:x[1])[0] if known else None
        dfts=[s.total_dft for s in systems]; comparison.thinnest_index=dfts.index(min(dfts)); comparison.thickest_index=dfts.index(max(dfts))
        counts=[len(s.layers) for s in systems]; comparison.fewest_layers_index=counts.index(min(counts)); comparison.best_balance_index=None
    def to_table(self,comparison:ComparisonResult)->list[dict]:
        systems=comparison.systems; names=[s.system.system_name or f"Система {i+1}" for i,s in enumerate(systems)]
        def row(label,values,highlight_min=False,highlight_max=False):
            result={"indicator":label}
            for i,value in enumerate(values): result[f"sys_{i}"]=value
            numeric=[v for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)]
            if highlight_min and numeric: result["_min_idx"]=values.index(min(numeric))
            if highlight_max and numeric: result["_max_idx"]=values.index(max(numeric))
            return result
        rows=[row("Название",names),row("Количество слоёв",[len(s.layers) for s in systems],True),row("Общая толщина DFT, мкм",[s.total_dft for s in systems],True,True),row("Расход ЛКМ, кг/м²",[s.total_practical_consumption_kg for s in systems],True),row("Расход ЛКМ, л/м²",[s.total_practical_consumption_l for s in systems],True),row("Стоимость ЛКМ + разбавителя, руб/м²",[s.total_cost_per_m2 for s in systems],True,True),row("Стоимость объекта, руб",[s.total_cost for s in systems],True)]
        max_layers=max((len(s.layers) for s in systems),default=0)
        for n in range(max_layers):
            materials=[]; dfts=[]; consumptions=[]; costs=[]
            for s in systems:
                if n<len(s.layers):
                    lr=s.layers[n]; materials.append(lr.material.display_name()); dfts.append(lr.target_dft); consumptions.append(lr.practical_consumption_kg); costs.append(lr.cost_per_m2+lr.thinner_cost_per_m2 if lr.cost_per_m2 is not None and lr.thinner_cost_per_m2 is not None else None)
                else: materials.append("—"); dfts.append("—"); consumptions.append("—"); costs.append("—")
            rows.extend([row(f"Слой {n+1}: материал",materials),row(f"Слой {n+1}: DFT, мкм",dfts),row(f"Слой {n+1}: расход, кг/м²",consumptions),row(f"Слой {n+1}: стоимость, руб/м²",costs)])
        return rows
