"""Application service: подбор систем АКЗ."""
from __future__ import annotations
from app.domain.recommendation import RecommendationEngine, ScoreWeights
from app.domain.recommendation.rules import filter_systems
from app.services.tds_technology_bridge import enrich_filter_result_with_known_tds

class RecommendationService:
    def __init__(self, engine=None, weights=None, materials_provider=None):
        self.engine = engine or RecommendationEngine(weights=weights, materials_provider=materials_provider)

    def filter_with_known_tds(self, obj, systems, require_corrosion=True, require_durability=True):
        results = filter_systems(systems, obj, require_corrosion=require_corrosion, require_durability=require_durability)
        for fr in results:
            enrich_filter_result_with_known_tds(fr)
        return results

    def recommend(self, obj, systems, top_n=5, calculate_costs=True, require_corrosion=True, require_durability=True, apply_known_tds_dft=True):
        working = list(systems)
        tds_fail_notes = []
        if apply_known_tds_dft and working:
            enriched = self.filter_with_known_tds(obj, working, require_corrosion=require_corrosion, require_durability=require_durability)
            working = [fr.system for fr in enriched if fr.passed]
            for fr in enriched:
                if not fr.passed:
                    name = getattr(fr.system, "system_name", "") or "—"
                    reason = fr.reasons_fail[0] if fr.reasons_fail else "не прошла фильтр"
                    tds_fail_notes.append(f"«{name}»: {reason}")
        result = self.engine.recommend(obj=obj, systems=working, top_n=top_n, calculate_costs=calculate_costs,
            require_corrosion=require_corrosion, require_durability=require_durability)
        if apply_known_tds_dft and tds_fail_notes and not result.items:
            extra = "; ".join(tds_fail_notes[:5])
            result.message = f"{result.message} TDS/фильтр: {extra}" if result.message else f"TDS/фильтр: {extra}"
        return result

    def format_report(self, result):
        return self.engine.format_report(result)
