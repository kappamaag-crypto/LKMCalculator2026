"""Expanded KNOWN TDS rules, combined DFT check, dew-point UNKNOWN semantics."""

from __future__ import annotations

from app.domain.enums import MaterialType
from app.domain.models import Material, ObjectData
from app.domain.technology import check_application_technology, check_target_dft
from app.services.tds_known_rules import (
    known_dft_rule_for_material_name,
    known_tds_rules,
    resolve_document_id_for_material_name,
)
from app.services.tds_technology_bridge import check_target_dft_with_known_tds


def test_expanded_known_rules_cover_blank_line():
    rules = known_tds_rules()
    assert len(rules) >= 24  # 8 materials x 3 rules
    assert all(r.status == "KNOWN" for r in rules)
    for name, expected in [
        ("Blank HP", "BLANK_HP_TDS"),
        ("Blank MIO intermediate", "BLANK_MIO_TDS"),
        ("Blank Tank", "BLANK_TANK_TDS"),
        ("Blank Zinc primer", "BLANK_ZINC_TDS"),
        ("Blank DTM", "BLANK_DTM_TDS"),
        ("Blank One coating", "BLANK_ONE_TDS"),
    ]:
        assert resolve_document_id_for_material_name(name) == expected
        rule = known_dft_rule_for_material_name(name)
        assert rule is not None and rule.status == "KNOWN"


def test_hp_dft_range_enforced():
    material = Material(material_name="Грунт-эмаль Blank HP", material_type=MaterialType.PRIMER_ENAMEL)
    ok = check_target_dft_with_known_tds(material, 300)
    assert not ok.has_errors
    assert any(i.code == "TECH_TDS_DFT_OK" for i in ok.issues)
    low = check_target_dft_with_known_tds(material, 100)
    assert any(i.code == "TECH_TDS_DFT_BELOW_MIN" for i in low.errors)


def test_zinc_dft_range_enforced():
    material = Material(material_name="Blank Zinc", material_type=MaterialType.OTHER)
    high = check_target_dft_with_known_tds(material, 120)
    assert any(i.code == "TECH_TDS_DFT_ABOVE_MAX" for i in high.errors)


def test_dew_point_without_material_margin_is_unknown_not_blocking():
    material = Material(
        material_name="Test",
        material_type=MaterialType.OTHER,
        density=1.4,
        solids_by_volume_percent=70,
        min_dew_point_margin_c=None,
    )
    obj = ObjectData(surface_temperature=17, dew_point=15, relative_humidity=60)
    result = check_application_technology(obj, material)
    assert not result.blocking
    assert any(i.code == "TECH_DEW_POINT_MARGIN_UNKNOWN" for i in result.issues)


def test_dew_point_with_explicit_margin_still_blocks():
    material = Material(
        material_name="Test",
        material_type=MaterialType.OTHER,
        min_dew_point_margin_c=3,
    )
    obj = ObjectData(surface_temperature=17, dew_point=15)
    result = check_application_technology(obj, material)
    assert result.blocking
    assert any(i.code == "TECH_DEW_POINT_MARGIN" for i in result.issues)


def test_domain_check_target_dft_accepts_explicit_tds_bounds():
    material = Material(material_name="X", recommended_dft_min=None, recommended_dft_max=None)
    result = check_target_dft(material, 50, tds_dft_min=80, tds_dft_max=250, tds_rule_id="R1")
    assert any(i.code == "TECH_TDS_DFT_BELOW_MIN" for i in result.errors)
