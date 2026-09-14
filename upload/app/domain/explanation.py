"""Explanation Engine — source-traceable explanations of calculation results.

Доменный модуль: не импортирует services/ORM/UI.
Не изобретает инженерные значения. Отсутствующие данные = UNKNOWN.
Объясняет, *что* рассчитано и *на каком основании*, без UI-косметики.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from app.domain.models import LayerResult, SystemCalculationResult
from app.domain.engineering_context import EngineeringContext
from app.domain.normative import UNKNOWN


INFO = "INFO"
WARNING = "WARNING"
UNKNOWN_DATA = "UNKNOWN_DATA"
OK = "OK"


@dataclass(frozen=True)
class ExplanationItem:
    code: str
    level: str
    message: str
    scope: str = "system"
    material_name: str = ""
    layer_index: Optional[int] = None
    field: Optional[str] = None
    source_note: str = ""


@dataclass
class ExplanationReport:
    items: list[ExplanationItem] = field(default_factory=list)
    overall_status: str = OK

    def add(self, code: str, level: str, message: str, *, scope: str = "system", material_name: str = "", layer_index: Optional[int] = None, field: Optional[str] = None, source_note: str = "") -> None:
        self.items.append(ExplanationItem(code=code, level=level, message=message, scope=scope, material_name=material_name, layer_index=layer_index, field=field, source_note=source_note))
        self._recompute_overall()

    def _recompute_overall(self) -> None:
        levels = {i.level for i in self.items}
        if UNKNOWN_DATA in levels:
            self.overall_status = UNKNOWN_DATA
        elif WARNING in levels:
            self.overall_status = WARNING
        else:
            self.overall_status = OK

    def summary_lines(self) -> list[str]:
        lines = [f"Explanation overall: {self.overall_status}"]
        for it in self.items:
            prefix = f"[{it.level}]"
            if it.layer_index is not None:
                prefix += f" L{it.layer_index + 1}"
            if it.material_name:
                prefix += f" ({it.material_name})"
            lines.append(f"{prefix} {it.code}: {it.message}")
        return lines

    def has_unknown_data(self) -> bool:
        return self.overall_status == UNKNOWN_DATA


def explain_system_calculation(result: SystemCalculationResult) -> ExplanationReport:
    report = ExplanationReport()
    system_name = result.system.system_name or "Без имени"
    n_layers = len(result.layers)
    report.add("SYS_OVERVIEW", INFO, f"Система «{system_name}»: {n_layers} слой(ёв), суммарная DFT = {result.total_dft:g} мкм.", scope="system", source_note="SystemCalculationResult")
    if result.object_data.area_m2 is None:
        report.add("OBJ_AREA_UNKNOWN", UNKNOWN_DATA, "Площадь объекта (area_m2) не задана — абсолютные расходы по площади недоступны.", scope="system", field="area_m2")
    else:
        report.add("OBJ_AREA", OK, f"Площадь объекта: {result.object_data.area_m2:g} м².", scope="system", field="area_m2")
    _explain_engineering_context(report, result.engineering_context)
    for idx, layer in enumerate(result.layers):
        _explain_layer(report, idx, layer)
    if result.total_cost_per_m2 is None:
        report.add("COST_UNKNOWN", UNKNOWN_DATA, "Стоимость / м² = UNKNOWN (нет подтверждённых цен материалов или разбавителя).", scope="system", field="total_cost_per_m2", source_note="None ≠ 0")
    else:
        report.add("COST_KNOWN", OK, f"Стоимость / м² рассчитана: {result.total_cost_per_m2:g}.", scope="system", field="total_cost_per_m2")
    report.add("PRECISION_NOTE", INFO, "Промежуточные значения v3 не округляются; округление только при display/export.", scope="system", source_note="ED / §7")
    return report


def _explain_engineering_context(report: ExplanationReport, ctx: EngineeringContext) -> None:
    status = ctx.normative_status
    if status == UNKNOWN:
        report.add("CTX_NORMATIVE_UNKNOWN", UNKNOWN_DATA, "Нормативный / TDS-контекст: UNKNOWN (нет source-backed KNOWN rules).", scope="context", field="normative_model", source_note="EngineeringContext.normative_status")
    else:
        report.add("CTX_NORMATIVE_KNOWN", OK, "Нормативный / TDS-контекст: KNOWN (есть хотя бы одно явное правило).", scope="context", field="normative_model", source_note="EngineeringContext.normative_status")
    if ctx.has_known_surface_assessment:
        report.add("CTX_SURFACE_KNOWN", OK, "Оценка поверхности (подготовка/профиль) частично или полностью известна.", scope="context", field="surface_condition")
    else:
        report.add("CTX_SURFACE_UNKNOWN", UNKNOWN_DATA, "Оценка поверхности: UNKNOWN (подготовка и профиль не заданы как KNOWN).", scope="context", field="surface_condition")


def _explain_layer(report: ExplanationReport, idx: int, layer: LayerResult) -> None:
    mat = layer.material
    name = mat.display_name() if hasattr(mat, "display_name") else (mat.material_name or mat.brand or "материал")
    density_ok = mat.density is not None and mat.density > 0
    sv_ok = mat.solids_by_volume_percent is not None and mat.solids_by_volume_percent > 0
    if not density_ok:
        report.add("LAYER_DENSITY_MISSING", UNKNOWN_DATA, "Плотность (density) отсутствует или некорректна — расчёт массы/стоимости ограничен.", scope="layer", material_name=name, layer_index=idx, field="density", source_note="обязательный параметр; None ≠ 0")
    if not sv_ok:
        report.add("LAYER_SV_MISSING", UNKNOWN_DATA, "Объёмный сухой остаток (solids_by_volume_percent) отсутствует — DFT/WFT не может быть обоснован.", scope="layer", material_name=name, layer_index=idx, field="solids_by_volume_percent", source_note="массовый СО не подставляется")
    if density_ok and sv_ok:
        report.add("LAYER_DFT_BASIS", OK, f"DFT={layer.target_dft:g} мкм → WFT={layer.wft:g} мкм (только от solids_by_volume_percent={mat.solids_by_volume_percent:g} %).", scope="layer", material_name=name, layer_index=idx, field="wft", source_note="formulas.calculate_wft; mass solids не используется")
    losses = layer.losses_percent
    src = getattr(layer, "losses_source", "DEFAULT") or "DEFAULT"
    profile_name = getattr(layer, "losses_profile_name", "") or ""
    note = getattr(layer, "losses_note", "") or ""
    prov = f"source={src}"
    if profile_name:
        prov += f", profile={profile_name}"
    if note:
        prov += f", note={note}"
    if src == "DEFAULT" and losses == 0.0:
        report.add("LAYER_LOSSES_ZERO", INFO, f"Потери = 0.0 % (DEFAULT / legacy default_losses — не скрытый инженерный коэффициент). [{prov}]", scope="layer", material_name=name, layer_index=idx, field="losses_percent", source_note="LossProfile resolve order §28")
    elif src == "EXPLICIT":
        report.add("LAYER_LOSSES_EXPLICIT", OK, f"Применены потери {losses:g} % (EXPLICIT). [{prov}]", scope="layer", material_name=name, layer_index=idx, field="losses_percent", source_note="explicit → LossProfile → default_losses")
    elif src == "PROFILE":
        report.add("LAYER_LOSSES_PROFILE", OK, f"Применены потери {losses:g} % (PROFILE). [{prov}]", scope="layer", material_name=name, layer_index=idx, field="losses_percent", source_note="explicit → LossProfile → default_losses")
    else:
        report.add("LAYER_LOSSES_APPLIED", OK, f"Применены потери {losses:g} % ({src}). [{prov}]", scope="layer", material_name=name, layer_index=idx, field="losses_percent", source_note="explicit → LossProfile → default_losses")
    if mat.is_incomplete:
        report.add("LAYER_MATERIAL_INCOMPLETE", WARNING, "Материал помечен is_incomplete=True — часть полей может быть UNKNOWN.", scope="material", material_name=name, layer_index=idx, field="is_incomplete")


def format_explanation_text(report: ExplanationReport) -> str:
    return "\n".join(report.summary_lines())


def explain_pre_application(report: ExplanationReport, pre_app: "PreApplicationCheckResult") -> None:
    from app.domain.pre_application import READY, BLOCKED, INCOMPLETE
    status = pre_app.status
    if status == READY:
        level, code, msg = OK, "PREAPP_READY", "Pre-Application: READY — ошибок и критичных UNKNOWN по условиям нанесения нет."
    elif status == BLOCKED:
        level, code, msg = WARNING, "PREAPP_BLOCKED", "Pre-Application: BLOCKED — есть ошибки условий нанесения."
    else:
        level, code, msg = UNKNOWN_DATA, "PREAPP_INCOMPLETE", "Pre-Application: INCOMPLETE — ключевые данные UNKNOWN, готовность не подтверждена."
    report.add(code, level, msg, scope="context", source_note="PreApplicationCheckResult.status")
    for item in pre_app.items:
        lvl = WARNING if item.level in ("error", "warning") else INFO
        report.add(f"PREAPP_{item.code}", lvl, item.message, scope=item.scope or "object", material_name=item.material_name, field=item.field, source_note="PreApplicationItem")


def explain_chemical_resistance(report: ExplanationReport, chem: "ChemicalResistanceCheckResult") -> None:
    from app.domain.chemical_resistance import RESISTANT, NOT_RESISTANT, UNKNOWN as CHEM_UNKNOWN
    if not chem.outcomes:
        report.add("CHEM_EMPTY", UNKNOWN_DATA, "Химстойкость: нет исходов (пустой registry / нет KNOWN rules) → UNKNOWN.", scope="context", source_note="ChemicalResistanceCheckResult")
        return
    for mat_name, by_agent in sorted(chem.outcomes.items()):
        for agent_id, outcome in sorted(by_agent.items()):
            if outcome == RESISTANT:
                lvl, code = OK, "CHEM_RESISTANT"
            elif outcome == NOT_RESISTANT:
                lvl, code = WARNING, "CHEM_NOT_RESISTANT"
            else:
                lvl, code = UNKNOWN_DATA, "CHEM_UNKNOWN"
            report.add(code, lvl, f"Химстойкость: {mat_name} × {agent_id} → {outcome}.", scope="material", material_name=mat_name, field=agent_id, source_note="ChemicalResistanceCheckResult (source-backed only)")


def explain_recommendation_signals(report: ExplanationReport, *, reasons: Sequence[str] | None = None, warnings: Sequence[str] | None = None, limitations: Sequence[str] | None = None) -> None:
    for i, text in enumerate(reasons or ()):
        if text and str(text).strip():
            report.add(f"REC_REASON_{i}", INFO, str(text).strip(), scope="system", source_note="RecommendationItem.reasons")
    for i, text in enumerate(warnings or ()):
        if text and str(text).strip():
            report.add(f"REC_WARN_{i}", WARNING, str(text).strip(), scope="system", source_note="RecommendationItem.warnings")
    for i, text in enumerate(limitations or ()):
        if text and str(text).strip():
            report.add(f"REC_LIMIT_{i}", UNKNOWN_DATA, str(text).strip(), scope="system", source_note="RecommendationItem.limitations")


def explain_engineering_bundle(result: SystemCalculationResult, *, pre_app: "PreApplicationCheckResult | None" = None, chem: "ChemicalResistanceCheckResult | None" = None, recommendation_reasons: Sequence[str] | None = None, recommendation_warnings: Sequence[str] | None = None, recommendation_limitations: Sequence[str] | None = None) -> ExplanationReport:
    report = explain_system_calculation(result)
    if pre_app is not None:
        explain_pre_application(report, pre_app)
    if chem is not None:
        explain_chemical_resistance(report, chem)
    if recommendation_reasons or recommendation_warnings or recommendation_limitations:
        explain_recommendation_signals(report, reasons=recommendation_reasons, warnings=recommendation_warnings, limitations=recommendation_limitations)
    return report
