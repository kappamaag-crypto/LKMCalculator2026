"""Bridge KNOWN TDS rules into technology checks without inventing limits.

When a KNOWN DFT rule is available for the material, target DFT is checked
against the TDS range. When no KNOWN rule exists, the result stays informational
UNKNOWN — material.recommended_dft_* is not treated as TDS proof.
"""

from __future__ import annotations

from typing import Optional

from app.domain.models import Material
from app.domain.technology import TechnologyCheckResult, check_target_dft
from app.services.tds_known_rules import known_dft_rule_for_material_name
from app.services.tds_manifest import TDSRule
from app.services.tds_rule_promotion import parse_dft_range_um


def check_target_dft_against_known_tds(
    material: Material,
    target_dft: Optional[float],
    dft_rule: TDSRule | None = None,
) -> TechnologyCheckResult:
    """Validate target DFT using an explicitly promoted KNOWN TDS rule only."""
    result = TechnologyCheckResult()
    rule = dft_rule
    if rule is None:
        rule = known_dft_rule_for_material_name(material.material_name or material.display_name())

    if rule is None or rule.status != "KNOWN":
        result.add_info(
            "TECH_TDS_DFT_UNKNOWN",
            "Нет KNOWN TDS-правила по DFT для материала — TDS-проверка толщины невозможна.",
            "target_dft",
        )
        return result

    if target_dft is None:
        result.add_info(
            "TECH_TARGET_DFT_UNKNOWN",
            "Целевая DFT не задана — проверка по TDS невозможна.",
            "target_dft",
        )
        return result

    if target_dft < 0:
        result.add_error(
            "TECH_TARGET_DFT_NEGATIVE",
            "Целевая DFT не может быть отрицательной.",
            "target_dft",
        )
        return result

    parsed = parse_dft_range_um(str(rule.value))
    if parsed is None:
        result.add_info(
            "TECH_TDS_DFT_UNPARSEABLE",
            f"KNOWN TDS rule {rule.rule_id} value «{rule.value}» cannot be parsed as a DFT range.",
            "target_dft",
        )
        return result

    dft_min, dft_max = parsed
    if target_dft < dft_min:
        result.add_error(
            "TECH_TDS_DFT_BELOW_MIN",
            f"Целевая DFT {target_dft:g} мкм ниже TDS-минимума {dft_min:g} мкм "
            f"({rule.rule_id}; {rule.locator}).",
            "target_dft",
        )
    elif target_dft > dft_max:
        result.add_error(
            "TECH_TDS_DFT_ABOVE_MAX",
            f"Целевая DFT {target_dft:g} мкм выше TDS-максимума {dft_max:g} мкм "
            f"({rule.rule_id}; {rule.locator}).",
            "target_dft",
        )
    else:
        result.add_info(
            "TECH_TDS_DFT_OK",
            f"Целевая DFT {target_dft:g} мкм соответствует TDS-диапазону "
            f"{dft_min:g}–{dft_max:g} мкм ({rule.rule_id}).",
            "target_dft",
        )
    return result


def check_target_dft_with_known_tds(
    material: Material,
    target_dft: Optional[float],
) -> TechnologyCheckResult:
    """Combine material-card DFT checks with KNOWN TDS bounds when available.

    Domain check_target_dft stays free of service imports; this service resolves
    KNOWN rules and passes explicit numeric bounds into the domain function.
    """
    rule = known_dft_rule_for_material_name(material.material_name or material.display_name())
    tds_min = tds_max = None
    rule_id = locator = None
    if rule is not None and rule.status == "KNOWN":
        parsed = parse_dft_range_um(str(rule.value))
        if parsed is not None:
            tds_min, tds_max = parsed
            rule_id = rule.rule_id
            locator = rule.locator

    result = check_target_dft(
        material,
        target_dft,
        tds_dft_min=tds_min,
        tds_dft_max=tds_max,
        tds_rule_id=rule_id,
        tds_locator=locator,
    )
    if rule is None or rule.status != "KNOWN" or tds_min is None:
        if target_dft is not None and target_dft >= 0:
            result.add_info(
                "TECH_TDS_DFT_UNKNOWN",
                "Нет KNOWN TDS-правила по DFT для материала — TDS-проверка толщины невозможна.",
                "target_dft",
            )
    return result


def enrich_filter_result_with_known_tds(result) -> None:
    for layer in result.system.layers:
        material = layer.material
        if material is None:
            continue
        tds = check_target_dft_with_known_tds(material, layer.target_dft)
        for issue in tds.issues:
            prefix = f"Слой {layer.layer_number}: "
            if issue.level == "error" and issue.code.startswith("TECH_TDS_"):
                result.passed = False
                result.reasons_fail.append(prefix + issue.message)
            elif issue.code.startswith("TECH_TDS_"):
                result.notes.append(prefix + issue.message)
