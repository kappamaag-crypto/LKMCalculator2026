"""Pre-Application Check (§23): READY / BLOCKED / INCOMPLETE, no invented limits."""

from app.domain.enums import MaterialType, PreparationGrade
from app.domain.models import Material, ObjectData
from app.domain.normative import NormativeSource
from app.domain.pre_application import (
    BLOCKED,
    INCOMPLETE,
    READY,
    check_pre_application,
)
from app.domain.surface_profile import SurfaceCondition, SurfacePreparation, SurfaceProfile
from app.services.calculation_service import CalculationService


def make_material(**kwargs):
    values = {
        "material_name": "Test coating",
        "material_type": MaterialType.EPOXY,
        "density": 1.4,
        "solids_by_volume_percent": 70,
        "min_application_temperature": 5,
        "max_application_temperature": 40,
        "max_relative_humidity": 80,
        "min_dew_point_margin_c": 3,
        "recommended_dft_min": 80,
        "recommended_dft_max": 200,
        "max_single_layer_dft": 250,
    }
    values.update(kwargs)
    return Material(**values)


def make_object(**kwargs):
    values = {
        "air_temperature": 20,
        "surface_temperature": 20,
        "relative_humidity": 60,
        "dew_point": 12,
    }
    values.update(kwargs)
    return ObjectData(**values)


def test_ready_when_ambient_and_limits_ok():
    obj = make_object(preparation=PreparationGrade.SA_2_5, roughness=50.0)
    result = check_pre_application(obj, [make_material()], actual_dfts=[120])
    assert result.status == READY, result.summary_lines()
    assert result.ready
    assert not result.has_errors


def test_blocked_when_dew_point_margin_too_low():
    obj = make_object(surface_temperature=15, dew_point=14)
    result = check_pre_application(obj, [make_material()], actual_dfts=[120])
    assert result.status == BLOCKED
    assert result.has_errors
    codes = [i.code for i in result.items]
    mat_codes = [iss.code for _, tech in result.material_results for iss in tech.issues]
    assert "TECH_DEW_POINT_MARGIN" in mat_codes or any("DEW" in c for c in codes + mat_codes)


def test_incomplete_when_ambient_missing():
    obj = ObjectData()
    result = check_pre_application(obj, [make_material()])
    assert result.status == INCOMPLETE
    assert any(i.code == "PRE_AMBIENT_UNKNOWN" for i in result.items)


def test_incomplete_when_material_has_no_limits():
    mat = make_material(
        min_application_temperature=None,
        max_application_temperature=None,
        max_relative_humidity=None,
        min_dew_point_margin_c=None,
    )
    result = check_pre_application(make_object(), [mat], actual_dfts=[120])
    assert result.status == INCOMPLETE
    assert any(i.code == "PRE_MATERIAL_LIMITS_UNKNOWN" for i in result.items)


def test_no_invented_dew_margin_when_material_limit_absent():
    """Missing min_dew_point_margin_c must not become 3 °C."""
    mat = make_material(min_dew_point_margin_c=None)
    obj = make_object(surface_temperature=15, dew_point=14)
    result = check_pre_application(obj, [mat], actual_dfts=[120])
    mat_codes = [iss.code for _, tech in result.material_results for iss in tech.issues]
    assert "TECH_DEW_POINT_MARGIN" not in mat_codes
    assert any(
        iss.code == "TECH_DEW_POINT_MARGIN_UNKNOWN" for _, tech in result.material_results for iss in tech.issues
    )


def test_surface_known_prep_recorded():
    src = NormativeSource(document_id="ISO 8501-1", title="Preparation of steel substrates")
    condition = SurfaceCondition(
        preparation=SurfacePreparation(method="Sa", grade="Sa 2.5", standard=src, assessment="KNOWN"),
        profile=SurfaceProfile(measurement="Rz", nominal_um=50, standard=src, assessment="KNOWN"),
    )
    result = check_pre_application(make_object(), [make_material()], surface_condition=condition, actual_dfts=[120])
    assert any(i.code == "PRE_SURFACE_PREP_KNOWN" for i in result.items)
    assert any(i.code == "PRE_SURFACE_PROFILE_KNOWN" for i in result.items)
    assert result.status == READY


def test_contamination_unacceptable_blocks():
    condition = SurfaceCondition(contamination_status="UNACCEPTABLE")
    result = check_pre_application(make_object(), [make_material()], surface_condition=condition, actual_dfts=[120])
    assert result.status == BLOCKED
    assert any(i.code == "PRE_SURFACE_CONTAMINATION" for i in result.items)


def test_calculation_service_run_pre_application_check():
    svc = CalculationService()
    result = svc.run_pre_application_check(make_object(), [make_material()], actual_dfts=[100])
    assert result.status in {READY, INCOMPLETE, BLOCKED}
    assert isinstance(result.summary_lines(), list)
    assert result.summary_lines()[0].startswith("Pre-Application:")


def test_blocked_when_relative_humidity_exceeds_material_limit():
    mat = make_material(max_relative_humidity=70)
    obj = make_object(relative_humidity=85)
    result = check_pre_application(obj, [mat], actual_dfts=[120])
    assert result.status == BLOCKED
    mat_codes = [iss.code for _, tech in result.material_results for iss in tech.issues]
    assert any("RH" in c or "HUMID" in c for c in mat_codes) or result.has_errors


def test_blocked_when_surface_below_dew_point():
    obj = make_object(surface_temperature=10, dew_point=12)
    result = check_pre_application(obj, [make_material()], actual_dfts=[120])
    assert result.status == BLOCKED
    assert any(i.code == "PRE_DEW_POINT_NEGATIVE" for i in result.items)


def test_incomplete_when_only_air_temperature_missing_rh_still_flagged():
    obj = ObjectData(air_temperature=20, surface_temperature=20, dew_point=10)
    result = check_pre_application(obj, [make_material()], actual_dfts=[120])
    assert any(i.code == "PRE_AMBIENT_UNKNOWN" for i in result.items)
