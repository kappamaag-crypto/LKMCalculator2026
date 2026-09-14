"""Tests for the opt-in source-backed chemical recommendation filter."""
from __future__ import annotations

from app.domain.chemical_resistance import ChemicalAgent, ChemicalResistanceRule, NOT_RESISTANT, RESISTANT
from app.domain.models import CoatingSystem, LayerDefinition, Material
from app.domain.enums import BinderType, CorrosionCategory, DurabilityLevel, EnvironmentType, MaterialType, SurfaceType
from app.domain.normative import NormativeSource
from app.services.recommendation_service import RecommendationService


def make_system(name="System"):
    material = Material(material_name=f"{name} material", material_type=MaterialType.PRIMER, binder_type=BinderType.EPOXY, density=1.4, solids_percent=70.0, solids_by_volume_percent=70.0)
    return CoatingSystem(id=1, system_name=name, corrosion_categories=[CorrosionCategory.C4], durability=DurabilityLevel.HIGH, temperature_min=-40, temperature_max=60, surface_types=[SurfaceType.NEW_STEEL], environments=[EnvironmentType.OUTDOOR], layers=[LayerDefinition(layer_number=1, target_dft=80.0, material=material)], number_of_layers=1)


def rule_for(name, outcome=RESISTANT, limit=None):
    return ChemicalResistanceRule(rule_id="CR-TEST", material_hint=name, agent_id="AGENT", status="KNOWN", outcome=outcome, source=NormativeSource(document_id="TDS-TEST"), concentration_max_percent=limit)


def test_unknown_is_hard_filter_by_default():
    system = make_system()
    result = RecommendationService().filter_with_chemical_resistance([system], [ChemicalAgent("AGENT")], [], require_known=True)[0]
    assert not result.passed
    assert result.insufficient_data
    assert "UNKNOWN" in result.reasons_fail[0]


def test_known_resistant_allows_candidate():
    system = make_system()
    result = RecommendationService().filter_with_chemical_resistance([system], [ChemicalAgent("AGENT")], [rule_for(system.layers[0].material.material_name)])[0]
    assert result.passed
    assert any("Химстойкость подтверждена" in text for text in result.reasons_pass)


def test_known_not_resistant_rejects_candidate():
    system = make_system()
    result = RecommendationService().filter_with_chemical_resistance([system], [ChemicalAgent("AGENT")], [rule_for(system.layers[0].material.material_name, outcome=NOT_RESISTANT)])[0]
    assert not result.passed
    assert any("не устойчив" in text.lower() for text in result.reasons_fail)


def test_explicit_concentration_limit_rejects_candidate():
    system = make_system()
    result = RecommendationService().filter_with_chemical_resistance([system], [ChemicalAgent("AGENT", concentration_percent=10.0)], [rule_for(system.layers[0].material.material_name, limit=5.0)])[0]
    assert not result.passed
    assert any("Концентрация" in text for text in result.reasons_fail)


def test_unknown_can_be_kept_only_when_explicitly_requested():
    system = make_system()
    result = RecommendationService().filter_with_chemical_resistance([system], [ChemicalAgent("AGENT")], [], require_known=False)[0]
    assert result.passed
    assert any("UNKNOWN" in text for text in result.notes)
