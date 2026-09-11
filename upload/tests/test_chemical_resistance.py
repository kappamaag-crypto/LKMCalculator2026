"""§24: chemical resistance only through source-backed rules."""

import pytest

from app.domain.chemical_resistance import (
    NOT_RESISTANT,
    RESISTANT,
    ChemicalAgent,
    ChemicalResistanceRule,
    check_chemical_resistance,
    resolve_rule,
)
from app.domain.normative import NormativeSource, UNKNOWN
from app.services.calculation_service import CalculationService
from app.services.chemical_resistance_rules import (
    clear_known_chemical_resistance_rules_for_tests,
    list_known_chemical_resistance_rules,
    make_rule,
    promote_chemical_resistance_rule,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_known_chemical_resistance_rules_for_tests()
    yield
    clear_known_chemical_resistance_rules_for_tests()


def test_empty_rules_yield_unknown_not_resistant():
    result = check_chemical_resistance(
        ["Blank Tank LP"],
        [ChemicalAgent(agent_id="H2SO4", name="Серная кислота", concentration_percent=10)],
        rules=(),
    )
    assert result.outcomes["Blank Tank LP"]["H2SO4"] == UNKNOWN
    assert not result.all_resistant
    assert any(i.code == "CHEM_RESISTANCE_UNKNOWN" for i in result.items)


def test_known_resistant_rule_matches():
    src = NormativeSource(document_id="TDS-BLANK-TANK-LP", title="Blank Tank LP TDS")
    rule = ChemicalResistanceRule(
        rule_id="BLANK_TANK_LP_H2SO4_10",
        material_hint="Tank LP",
        agent_id="H2SO4",
        status="KNOWN",
        outcome=RESISTANT,
        source=src,
        concentration_max_percent=10,
        temperature_max_c=25,
    )
    result = check_chemical_resistance(
        ["Blank Tank LP Epoxy"],
        [ChemicalAgent(agent_id="H2SO4", concentration_percent=5, temperature_c=20)],
        rules=[rule],
    )
    assert result.outcomes["Blank Tank LP Epoxy"]["H2SO4"] == RESISTANT
    assert result.all_resistant


def test_concentration_exceeded_becomes_not_resistant():
    rule = make_rule(
        rule_id="R1",
        material_hint="Tank LP",
        agent_id="H2SO4",
        outcome=RESISTANT,
        document_id="TDS-1",
        concentration_max_percent=10,
    )
    result = check_chemical_resistance(
        ["Blank Tank LP"],
        [ChemicalAgent(agent_id="H2SO4", concentration_percent=30)],
        rules=[rule],
    )
    assert result.outcomes["Blank Tank LP"]["H2SO4"] == NOT_RESISTANT
    assert result.has_errors
    assert any(i.code == "CHEM_CONCENTRATION_EXCEEDED" for i in result.items)


def test_no_invention_from_binder_or_category():
    """Without rules, epoxy/C5 must still be UNKNOWN."""
    result = check_chemical_resistance(
        ["Generic Epoxy C5"],
        [ChemicalAgent(agent_id="NaOH")],
        rules=(),
    )
    assert result.outcomes["Generic Epoxy C5"]["NaOH"] == UNKNOWN


def test_promote_requires_verified_by_and_source():
    bad = ChemicalResistanceRule(
        rule_id="X",
        material_hint="X",
        agent_id="Y",
        status=UNKNOWN,
    )
    with pytest.raises(ValueError):
        promote_chemical_resistance_rule(bad, verified_by="tester")

    good = make_rule(
        rule_id="EFFA_01B_WATER",
        material_hint="EFFA 01B",
        agent_id="water",
        outcome=RESISTANT,
        document_id="EFFA-01B-TDS",
    )
    with pytest.raises(ValueError):
        promote_chemical_resistance_rule(good, verified_by="  ")

    promoted = promote_chemical_resistance_rule(good, verified_by="inspector@akz")
    assert promoted.is_known
    assert len(list_known_chemical_resistance_rules()) == 1


def test_longest_hint_resolve():
    rules = [
        make_rule(rule_id="A", material_hint="Tank", agent_id="oil", outcome=RESISTANT, document_id="D1"),
        make_rule(rule_id="B", material_hint="Tank LP", agent_id="oil", outcome=NOT_RESISTANT, document_id="D2"),
    ]
    matched = resolve_rule("Blank Tank LP Interior", "oil", rules)
    assert matched is not None
    assert matched.rule_id == "B"


def test_require_known_turns_unknown_into_error():
    result = check_chemical_resistance(
        ["Unknown Coat"],
        [ChemicalAgent(agent_id="HCl")],
        rules=(),
        require_known=True,
    )
    assert result.has_errors
    assert result.outcomes["Unknown Coat"]["HCl"] == UNKNOWN


def test_calculation_service_uses_registry():
    promote_chemical_resistance_rule(
        make_rule(
            rule_id="SVC1",
            material_hint="EFFA",
            agent_id="freshwater",
            outcome=RESISTANT,
            document_id="EFFA-DOC",
        ),
        verified_by="test",
    )
    svc = CalculationService()
    result = svc.check_chemical_resistance(
        ["EFFA 01B"],
        [ChemicalAgent(agent_id="freshwater")],
    )
    assert result.outcomes["EFFA 01B"]["freshwater"] == RESISTANT


def test_known_rule_without_source_rejected():
    with pytest.raises(ValueError):
        ChemicalResistanceRule(
            rule_id="bad",
            material_hint="x",
            agent_id="y",
            status="KNOWN",
            outcome=RESISTANT,
            source=None,
        )
