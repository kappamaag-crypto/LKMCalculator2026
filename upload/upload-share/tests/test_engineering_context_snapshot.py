"""Regression tests for source-preserving engineering-context snapshots."""
from __future__ import annotations

from datetime import date

from app.domain.engineering_context import EngineeringContext
from app.domain.normative import NormativeModel, NormativeRule, NormativeSource, UNKNOWN
from app.domain.surface_profile import SurfaceCondition, SurfacePreparation, SurfaceProfile
from app.services.engineering_context_snapshot import (
    engineering_context_from_dict,
    engineering_context_to_dict,
)


def _context() -> EngineeringContext:
    source = NormativeSource(
        document_id="TDS-001",
        title="Verified TDS",
        revision="2026-01",
        effective_from=date(2026, 1, 1),
        issuer="SPKEFFA",
        source_uri="sha256:" + "a" * 64,
    )
    rule = NormativeRule(
        rule_id="dft.min",
        value=80,
        status="KNOWN",
        source=source,
        applicability="primer",
        notes="locator=table-1",
    )
    model = NormativeModel(
        model_id="spk-effa-tds",
        version="8",
        rules={rule.rule_id: rule},
        description="Explicitly promoted TDS rules",
    )
    condition = SurfaceCondition(
        preparation=SurfacePreparation(
            method="Sa",
            grade="Sa 2.5",
            standard=source,
            assessment=UNKNOWN,
            notes="source-backed standard identity only",
        ),
        profile=SurfaceProfile(
            measurement="UNKNOWN",
            nominal_um=50,
            standard=source,
            assessment=UNKNOWN,
        ),
        substrate="steel",
        contamination_status=UNKNOWN,
        moisture_status=UNKNOWN,
    )
    return EngineeringContext(normative_model=model, surface_condition=condition)


def test_engineering_context_round_trip_preserves_source_and_unknown_state():
    original = _context()
    restored = engineering_context_from_dict(engineering_context_to_dict(original))

    assert restored is not None
    assert restored.normative_model is not None
    rule = restored.normative_model.rule("dft.min")
    assert rule.status == "KNOWN"
    assert rule.value == 80
    assert rule.source is not None
    assert rule.source.document_id == "TDS-001"
    assert rule.source.revision == "2026-01"
    assert rule.source.source_uri == "sha256:" + "a" * 64
    assert restored.surface_condition.preparation.grade == "Sa 2.5"
    assert restored.surface_condition.preparation.assessment == UNKNOWN
    assert restored.surface_condition.profile.measurement == UNKNOWN
    assert restored.surface_condition.profile.nominal_um == 50


def test_empty_normative_and_surface_context_does_not_become_known():
    restored = engineering_context_from_dict({})

    assert restored is not None
    assert restored.normative_model is None
    assert restored.surface_condition.preparation.assessment == UNKNOWN
    assert restored.surface_condition.profile.measurement == UNKNOWN
    assert restored.surface_condition.contamination_status == UNKNOWN
    assert restored.surface_condition.moisture_status == UNKNOWN
