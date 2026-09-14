"""Service registry of source-backed chemical resistance rules.

Rules enter only via explicit promote_chemical_resistance_rule (no auto-promotion).
Empty catalog by default: absence of rules ⇒ UNKNOWN, never invented resistance.
"""

from __future__ import annotations

from typing import Sequence

from app.domain.chemical_resistance import ChemicalResistanceRule
from app.domain.normative import NormativeSource, UNKNOWN

# Explicitly promoted KNOWN rules. Populate only after verified source text + identity.
# Intentionally empty at bootstrap: §24 forbids inventing resistance.
_KNOWN_CHEMICAL_RESISTANCE_RULES: list[ChemicalResistanceRule] = []


def list_known_chemical_resistance_rules() -> tuple[ChemicalResistanceRule, ...]:
    return tuple(_KNOWN_CHEMICAL_RESISTANCE_RULES)


def promote_chemical_resistance_rule(
    rule: ChemicalResistanceRule,
    *,
    verified_by: str,
) -> ChemicalResistanceRule:
    """Gate: only KNOWN rules with source and non-empty verified_by may be registered."""
    if not verified_by.strip():
        raise ValueError("verified_by is required for chemical resistance promotion")
    if rule.status != "KNOWN":
        raise ValueError("only KNOWN chemical resistance rules can be promoted")
    if rule.source is None:
        raise ValueError("KNOWN rule requires NormativeSource")
    if rule.outcome not in {"RESISTANT", "NOT_RESISTANT"}:
        raise ValueError("KNOWN rule outcome must be RESISTANT or NOT_RESISTANT")
    # Replace same rule_id if re-promoted
    global _KNOWN_CHEMICAL_RESISTANCE_RULES
    _KNOWN_CHEMICAL_RESISTANCE_RULES = [r for r in _KNOWN_CHEMICAL_RESISTANCE_RULES if r.rule_id != rule.rule_id]
    _KNOWN_CHEMICAL_RESISTANCE_RULES.append(rule)
    return rule


def clear_known_chemical_resistance_rules_for_tests() -> None:
    """Test helper: reset registry."""
    global _KNOWN_CHEMICAL_RESISTANCE_RULES
    _KNOWN_CHEMICAL_RESISTANCE_RULES = []


def make_rule(
    *,
    rule_id: str,
    material_hint: str,
    agent_id: str,
    outcome: str,
    document_id: str,
    title: str = "",
    concentration_max_percent: float | None = None,
    temperature_max_c: float | None = None,
    notes: str = "",
) -> ChemicalResistanceRule:
    """Helper to build a KNOWN rule with NormativeSource."""
    return ChemicalResistanceRule(
        rule_id=rule_id,
        material_hint=material_hint,
        agent_id=agent_id,
        status="KNOWN",
        outcome=outcome,
        source=NormativeSource(document_id=document_id, title=title or document_id),
        concentration_max_percent=concentration_max_percent,
        temperature_max_c=temperature_max_c,
        notes=notes,
    )
