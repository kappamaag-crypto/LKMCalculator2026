"""Application service: подбор систем АКЗ."""
from __future__ import annotations

from app.domain.chemical_resistance import (
    ChemicalAgent,
    ChemicalResistanceRule,
    NOT_RESISTANT,
    UNKNOWN,
    check_chemical_resistance,
)
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

    def filter_with_chemical_resistance(
        self,
        systems,
        agents,
        rules,
        *,
        require_known=True,
    ):
        """Apply an explicit chemical-resistance hard filter to recommendation candidates.

        The filter is opt-in: callers must provide chemical agents. Unknown evidence is
        never treated as resistant; with require_known=True it removes the candidate.
        No binder/category inference is performed.
        """
        results = []
        for system in systems:
            material_names = []
            missing_material = False
            for layer in getattr(system, "layers", []) or []:
                material = getattr(layer, "material", None)
                name = getattr(material, "material_name", None) if material is not None else None
                if name:
                    material_names.append(name)
                else:
                    missing_material = True

            if missing_material or not material_names:
                # Reuse the existing FilterResult shape without inventing a material name.
                from app.domain.recommendation.rules import FilterResult
                fr = FilterResult(system=system, passed=False, insufficient_data=True)
                fr.reasons_fail.append("Недостаточно данных: материалы системы не определены для проверки химстойкости")
                results.append(fr)
                continue

            check = check_chemical_resistance(
                material_names,
                agents,
                rules,
                require_known=require_known,
            )
            from app.domain.recommendation.rules import FilterResult
            fr = FilterResult(system=system, passed=True)
            for issue in check.items:
                if issue.level == "error":
                    fr.passed = False
                    fr.reasons_fail.append(issue.message)
                    if issue.code == "CHEM_RESISTANCE_UNKNOWN":
                        fr.insufficient_data = True
                else:
                    fr.notes.append(issue.message)

            if any(outcome == NOT_RESISTANT for by_agent in check.outcomes.values() for outcome in by_agent.values()):
                fr.passed = False
            if any(outcome == UNKNOWN for by_agent in check.outcomes.values() for outcome in by_agent.values()):
                if require_known:
                    fr.passed = False
                    fr.insufficient_data = True
                else:
                    fr.notes.append("Химстойкость UNKNOWN: кандидат не исключён, так как require_known=False")
            if fr.passed:
                fr.reasons_pass.append("Химстойкость подтверждена для заданных агентов")
            results.append(fr)
        return results

    def recommend(
        self,
        obj,
        systems,
        top_n=5,
        calculate_costs=True,
        require_corrosion=True,
        require_durability=True,
        apply_known_tds_dft=True,
        chemical_agents=None,
        chemical_rules=None,
        require_known_chemical=True,
    ):
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

        chemical_fail_notes = []
        if chemical_agents:
            chem_results = self.filter_with_chemical_resistance(
                working,
                chemical_agents,
                chemical_rules or [],
                require_known=require_known_chemical,
            )
            working = [fr.system for fr in chem_results if fr.passed]
            for fr in chem_results:
                if not fr.passed:
                    name = getattr(fr.system, "system_name", "") or "—"
                    reason = fr.reasons_fail[0] if fr.reasons_fail else "не прошла фильтр химстойкости"
                    chemical_fail_notes.append(f"«{name}»: {reason}")

        result = self.engine.recommend(
            obj=obj,
            systems=working,
            top_n=top_n,
            calculate_costs=calculate_costs,
            require_corrosion=require_corrosion,
            require_durability=require_durability,
        )
        notes = tds_fail_notes + chemical_fail_notes
        if notes and not result.items:
            extra = "; ".join(notes[:5])
            result.message = f"{result.message} TDS/химстойкость: {extra}" if result.message else f"TDS/химстойкость: {extra}"
        return result

    def format_report(self, result):
        return self.engine.format_report(result)
