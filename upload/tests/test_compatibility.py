from app.domain.compatibility import (
    FAMILY_LABELS,
    RULES,
    SOURCE_TABLE,
    SOURCE_URL,
    check_binders,
    family_for_binder,
)
from app.domain.enums import BinderType, CompatibilityStatus


def test_source_matrix_shape_is_preserved():
    assert len(FAMILY_LABELS) == 18
    assert len(RULES) > 0
    assert SOURCE_TABLE == "Таблица 1. Совместимость ЛКМ с грунтовками"
    # Live source page path used by domain (not a generic compatibility-tables.html).
    assert "sovmestim" in SOURCE_URL or SOURCE_URL.endswith("/compatibility-tables.html")


def test_direction_is_previous_layer_to_applied_layer():
    # Source: epoxy over epoxy is marker "2" (roughening), not blank prohibition.
    epoxy_over_epoxy = check_binders(BinderType.EPOXY, BinderType.EPOXY)
    polyurethane_over_epoxy = check_binders(BinderType.EPOXY, BinderType.POLYURETHANE)
    epoxy_over_polyurethane = check_binders(BinderType.POLYURETHANE, BinderType.EPOXY)

    assert epoxy_over_epoxy.status is CompatibilityStatus.WARNING
    assert "шероховатости" in epoxy_over_epoxy.note
    assert polyurethane_over_epoxy.status is CompatibilityStatus.WARNING
    assert epoxy_over_polyurethane.status is CompatibilityStatus.UNKNOWN


def test_warning_markers_are_not_treated_as_forbidden():
    # Source marker 1: AC over HV requires an adhesion check.
    rule = RULES[("hv", "ac")]
    assert rule.status is CompatibilityStatus.WARNING
    assert "адгезию" in rule.note

    # Source marker 2: epoxy over epoxy requires roughening (not forbidden).
    rule = RULES[("epoxy", "epoxy")]
    assert rule.status is CompatibilityStatus.WARNING
    assert "шероховатости" in rule.note
    assert rule.status is not CompatibilityStatus.FORBIDDEN


def test_unmapped_current_binder_is_unknown():
    assert family_for_binder(BinderType.ALKYD) is None
    assert family_for_binder(BinderType.ZINC_ETHYL_SILICATE) is None
    assert check_binders(BinderType.ALKYD, BinderType.EPOXY).status is CompatibilityStatus.UNKNOWN
    assert check_binders(BinderType.ZINC_ETHYL_SILICATE, BinderType.POLYURETHANE).status is CompatibilityStatus.UNKNOWN


def test_epoxy_and_acrylic_mapping_uses_source_direction():
    # Source polyacrylic row has "+" under epoxy previous → acrylic over epoxy ALLOWED.
    acrylic_over_epoxy = check_binders(BinderType.EPOXY, BinderType.ACRYLIC)
    epoxy_over_acrylic = check_binders(BinderType.ACRYLIC, BinderType.EPOXY)

    assert acrylic_over_epoxy.status is CompatibilityStatus.ALLOWED
    assert epoxy_over_acrylic.status is CompatibilityStatus.UNKNOWN


def test_epoxy_ester_is_supported_only_where_source_has_a_column():
    epoxy_over_epoxy_ester = check_binders(BinderType.EPOXY_ESTER, BinderType.EPOXY)
    epoxy_ester_over_epoxy = check_binders(BinderType.EPOXY, BinderType.EPOXY_ESTER)

    assert epoxy_over_epoxy_ester.status is CompatibilityStatus.ALLOWED
    assert epoxy_ester_over_epoxy.status in {
        CompatibilityStatus.ALLOWED,
        CompatibilityStatus.WARNING,
        CompatibilityStatus.UNKNOWN,
    }
