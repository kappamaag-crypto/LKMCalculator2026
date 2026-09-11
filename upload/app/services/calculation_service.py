"""Application service: расчёты и сравнение."""

from __future__ import annotations

from typing import Optional, Sequence

from app.domain.models import (
    Material,
    ObjectData,
    CoatingSystem,
    SystemCalculationResult,
    ComparisonResult,
)
from app.domain.calculator import SystemCalculator, LayerInput, LayerCalculator
from app.domain.comparison import ComparisonEngine
from app.domain.engineering_context import EngineeringContext
from app.domain.layer_compatibility import LayerCompatibilityEngine
from app.domain.validation import ValidationResult
from app.domain.technology import TechnologyCheckResult
from app.domain.pre_application import PreApplicationCheckResult, check_pre_application
from app.domain.surface_profile import SurfaceCondition
from app.services.tds_technology_bridge import check_target_dft_with_known_tds
from app.services.tds_normative_bridge import engineering_context_from_known_tds, tds_trace_for_material
from app.domain.chemical_resistance import (
    ChemicalAgent,
    ChemicalResistanceCheckResult,
    check_chemical_resistance,
)
from app.services.chemical_resistance_rules import list_known_chemical_resistance_rules
from app.domain.explanation import ExplanationReport, explain_system_calculation, format_explanation_text, explain_engineering_bundle


class CalculationService:
    """
    Сервис расчётов.

    Оркестрирует calculator + validation + (опционально) репозитории.
    Инженерные формулы остаются в domain/calculator.py и domain/formulas.py.
    """

    def __init__(
        self,
        calculator: Optional[SystemCalculator] = None,
        comparison_engine: Optional[ComparisonEngine] = None,
        compatibility_engine: Optional[LayerCompatibilityEngine] = None,
        default_losses: float = 0.0,
    ):
        self.calculator = calculator or SystemCalculator(default_losses=default_losses)
        self.comparison = comparison_engine or ComparisonEngine(self.calculator)
        self.compatibility = compatibility_engine or LayerCompatibilityEngine()

    def calculate_layer(
        self,
        material: Material,
        target_dft: float,
        losses_percent: float = 0.0,
        thinner_percent: float = 0.0,
        thinner: Optional[Material] = None,
        thinner_basis: Optional[str] = None,
        area_m2: float = 1.0,
    ):
        return LayerCalculator.calculate(
            material=material,
            target_dft=target_dft,
            losses_percent=losses_percent,
            thinner_percent=thinner_percent,
            thinner_basis=thinner_basis,
            thinner=thinner,
            area_m2=area_m2,
        )

    def calculate_system(
        self,
        obj: ObjectData,
        layers: Sequence[LayerInput],
        system: Optional[CoatingSystem] = None,
        engineering_context: EngineeringContext | None = None,
    ) -> tuple[SystemCalculationResult, ValidationResult]:
        return self.calculator.calculate(
            obj,
            layers,
            system=system,
            engineering_context=engineering_context,
        )

    def calculate_from_template(
        self,
        obj: ObjectData,
        template,
        materials_by_id=None,
        engineering_context: EngineeringContext | None = None,
    ):
        return self.calculator.calculate_from_template(
            obj,
            template,
            materials_by_id=materials_by_id,
            engineering_context=engineering_context,
        )

    def compare_systems(
        self,
        obj: ObjectData,
        systems: Sequence[CoatingSystem],
        materials_by_id=None,
    ) -> ComparisonResult:
        return self.comparison.compare(obj, systems, materials_by_id=materials_by_id)

    def compatibility_report(self, result: SystemCalculationResult):
        return self.compatibility.report(result)

    def check_system_tds_dft(self, system, materials_by_id=None):
        """Check target DFT of each layer against known TDS rules when available."""
        from app.services.tds_known_rules import resolve_material_document

        materials_by_id = materials_by_id or {}
        findings = []
        for layer in system.layers:
            mat = None
            if layer.material is not None:
                mat = layer.material
            elif layer.material_id is not None:
                mat = materials_by_id.get(layer.material_id)
            if mat is None:
                continue
            findings.append(
                check_target_dft_with_known_tds(
                    mat,
                    layer.target_dft or layer.dft_min or layer.dft_max,
                )
            )
        return findings

    def build_tds_engineering_context(self, system, materials_by_id=None, base=None):
        return engineering_context_from_known_tds(
            system, materials_by_id=materials_by_id, base=base
        )

    def tds_trace_for_system(self, system, materials_by_id=None):
        materials_by_id = materials_by_id or {}
        traces = []
        for layer in system.layers:
            mat = layer.material
            if mat is None and layer.material_id is not None:
                mat = materials_by_id.get(layer.material_id)
            if mat is None:
                continue
            traces.append(tds_trace_for_material(mat))
        return traces

    def check_chemical_resistance(
        self,
        material_names: Sequence[str],
        agents: Sequence[ChemicalAgent],
        *,
        require_known: bool = False,
        extra_rules: Sequence | None = None,
    ) -> ChemicalResistanceCheckResult:
        """Chemical resistance only via source-backed KNOWN rules (registry + optional extra).

        Empty registry ⇒ UNKNOWN for every pair; never invents resistance.
        """
        rules = list(list_known_chemical_resistance_rules())
        if extra_rules:
            rules.extend(extra_rules)
        return check_chemical_resistance(
            material_names,
            agents,
            rules,
            require_known=require_known,
        )

    def run_pre_application_check(
        self,
        obj: ObjectData,
        materials: Sequence[Material],
        *,
        surface_condition: SurfaceCondition | None = None,
        actual_dfts: Sequence[float | None] | None = None,
        engineering_context: EngineeringContext | None = None,
    ) -> PreApplicationCheckResult:
        """Pre-Application Check: ambient + surface + material technology limits.

        Surface condition may come from explicit argument or engineering_context.
        Domain check does not invent dew-point margins or TDS values.
        """
        surface = surface_condition
        if surface is None and engineering_context is not None:
            surface = engineering_context.surface_condition
        return check_pre_application(
            obj,
            materials,
            surface_condition=surface,
            actual_dfts=actual_dfts,
        )

    def explain_calculation(self, result: SystemCalculationResult) -> ExplanationReport:
        """Explanation Engine: source-traceable объяснение SystemCalculationResult.

        Domain-only logic; no invented values. Missing data → UNKNOWN_DATA.
        """
        return explain_system_calculation(result)

    def explain_engineering_bundle(
        self,
        result: SystemCalculationResult,
        *,
        pre_app: PreApplicationCheckResult | None = None,
        chem: ChemicalResistanceCheckResult | None = None,
        recommendation_reasons: Sequence[str] | None = None,
        recommendation_warnings: Sequence[str] | None = None,
        recommendation_limitations: Sequence[str] | None = None,
    ) -> ExplanationReport:
        """§26 integration: calculation + optional pre-app / chem / recommendation signals."""
        return explain_engineering_bundle(
            result,
            pre_app=pre_app,
            chem=chem,
            recommendation_reasons=recommendation_reasons,
            recommendation_warnings=recommendation_warnings,
            recommendation_limitations=recommendation_limitations,
        )

    def format_explanation(self, result: SystemCalculationResult) -> str:
        """Текстовый отчёт Explanation Engine."""
        return format_explanation_text(explain_system_calculation(result))

    def format_summary(self, result: SystemCalculationResult) -> str:
        """Краткая сводка расчёта, включая расход разбавителя и source-backed совместимость."""
        thinner_l_m2 = sum(lr.thinner_consumption_l for lr in result.layers)
        thinner_kg_m2 = sum(lr.thinner_consumption_kg for lr in result.layers)
        area = result.object_data.area_m2
        thinner_l_total = thinner_l_m2 * area if area is not None else None
        thinner_kg_total = thinner_kg_m2 * area if area is not None else None
        lines = [
            f"Система: {result.system.system_name}",
            f"Слоёв: {len(result.layers)}",
            f"Суммарная DFT: {result.total_dft:g} мкм",
            f"Стоимость / м²: {result.total_cost_per_m2:g}",
        ]
        if thinner_l_m2:
            lines.append(f"Разбавитель: {thinner_l_m2:g} л/м²")
        if thinner_l_total is not None:
            lines.append(f"Разбавитель всего: {thinner_l_total:g} л")

        if len(result.layers) >= 2:
            compatibility = self.compatibility_report(result)
            status_labels = {
                "разрешено": "РАЗРЕШЕНО",
                "предупреждение": "ПРЕДУПРЕЖДЕНИЕ",
                "запрещено": "ЗАПРЕЩЕНО",
                "нет подтвержденных данных": "UNKNOWN — НЕТ ПОДТВЕРЖДЁННЫХ ДАННЫХ",
            }
            lines.append(
                "Совместимость слоёв: "
                + status_labels.get(compatibility.status.value, compatibility.status.value)
            )
            for transition in compatibility.transitions:
                lines.append(f"{transition.message} [источник: {transition.rule.source}]")

        return "\n".join(lines)
