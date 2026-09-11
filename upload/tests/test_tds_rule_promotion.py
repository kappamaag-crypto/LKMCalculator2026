"""Tests for explicit TDS rule promotion and TDS-backed technology DFT checks."""

from __future__ import annotations

import pytest

from app.domain.models import Material
from app.domain.enums import MaterialType, BinderType
from app.services.spk_effa_tds_catalog import spk_effa_tds_by_id, blank_universal_staged_rules
from app.services.tds_known_rules import (
    known_dft_rule_for_material_name,
    known_tds_rules,
    resolve_document_id_for_material_name,
)
from app.services.tds_manifest import TDSRule, verify_manifest
from app.services.tds_rule_promotion import parse_dft_range_um, promote_tds_rule
from app.services.tds_technology_bridge import check_target_dft_against_known_tds


def test_cannot_promote_without_known_document() -> None:
    from app.services.tds_manifest import TDSDocument

    document = TDSDocument(
        document_id="X",
        title="X",
        repository="kappamaag-crypto/SPKEFFA",
        source_path="docs/blank/Blank_Universal.pdf",
        sha256=None,
        status="UNKNOWN",
    )
    rule = TDSRule(
        rule_id="R",
        document_id="X",
        value="80-250",
        locator="page 1",
        applicability="test",
        status="UNKNOWN",
    )
    with pytest.raises(ValueError, match="source document is not KNOWN"):
        promote_tds_rule(document, rule, verified_by="reviewer")


def test_promote_requires_verified_by() -> None:
    document = spk_effa_tds_by_id("BLANK_UNIVERSAL_TDS")
    assert document is not None
    staged = blank_universal_staged_rules()[0]
    with pytest.raises(ValueError, match="verified_by"):
        promote_tds_rule(document, staged, verified_by="  ")


def test_known_rules_are_promoted_and_manifest_valid() -> None:
    rules = known_tds_rules()
    assert len(rules) >= 6
    assert all(r.status == "KNOWN" for r in rules)
    document = spk_effa_tds_by_id("BLANK_UNIVERSAL_TDS")
    assert document is not None
    verify_manifest((document,), tuple(r for r in rules if r.document_id == document.document_id))


def test_parse_dft_range() -> None:
    assert parse_dft_range_um("80-250 мкм") == (80.0, 250.0)
    assert parse_dft_range_um("50–90 мкм") == (50.0, 90.0)
    assert parse_dft_range_um("not-a-range") is None


def test_material_name_resolves_to_document() -> None:
    assert resolve_document_id_for_material_name("Грунт-Эмаль Blank Universal") == "BLANK_UNIVERSAL_TDS"
    assert resolve_document_id_for_material_name("Эмаль Blank Finish") == "BLANK_FINISH_TDS"
    assert resolve_document_id_for_material_name("Unknown Coat") is None


def test_tds_dft_check_ok_and_out_of_range() -> None:
    material = Material(
        material_name="Грунт-Эмаль Blank Universal",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_by_volume_percent=73.0,
    )
    ok = check_target_dft_against_known_tds(material, 120)
    assert not ok.has_errors
    assert any(i.code == "TECH_TDS_DFT_OK" for i in ok.issues)

    low = check_target_dft_against_known_tds(material, 40)
    assert low.has_errors
    assert any(i.code == "TECH_TDS_DFT_BELOW_MIN" for i in low.errors)

    high = check_target_dft_against_known_tds(material, 300)
    assert high.has_errors
    assert any(i.code == "TECH_TDS_DFT_ABOVE_MAX" for i in high.errors)


def test_unknown_material_stays_unknown() -> None:
    material = Material(material_name="Mystery Primer XYZ")
    result = check_target_dft_against_known_tds(material, 100)
    assert not result.has_errors
    assert any(i.code == "TECH_TDS_DFT_UNKNOWN" for i in result.issues)


def test_known_dft_rule_lookup() -> None:
    rule = known_dft_rule_for_material_name("Blank Finish enamel")
    assert rule is not None
    assert rule.status == "KNOWN"
    assert rule.rule_id == "BLANK_FINISH_DFT_RANGE"
