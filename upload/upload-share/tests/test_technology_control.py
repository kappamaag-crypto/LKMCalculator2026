from app.domain.models import Material, ObjectData
from app.domain.technology_control import TechnologyCheckService


def test_dew_point_margin_passes_at_required_three_degrees():
    obj = ObjectData(surface_temperature=12.0, dew_point=9.0)
    result = TechnologyCheckService().check_application_conditions(obj, [])
    assert result.passed
    assert any(i.code == "DEW_POINT_MARGIN_PASS" for i in result.issues)


def test_dew_point_margin_is_blocking_error_below_requirement():
    obj = ObjectData(surface_temperature=11.0, dew_point=9.0)
    result = TechnologyCheckService().check_application_conditions(obj, [])
    assert not result.passed
    assert any(i.level == "error" and i.code == "DEW_POINT_MARGIN_FAIL" for i in result.issues)


def test_rh_above_material_limit_is_error():
    obj = ObjectData(relative_humidity=86.0)
    material = Material(material_name="Primer", max_relative_humidity=85.0)
    result = TechnologyCheckService().check_application_conditions(obj, [material])
    assert not result.passed
    assert any(i.code == "RH_TOO_HIGH" for i in result.errors)


def test_dft_below_material_min_is_error():
    material = Material(material_name="Primer", recommended_dft_min=80.0, recommended_dft_max=120.0)
    result = TechnologyCheckService().check_dft(material, 70.0, layer_index=1)
    assert not result.passed
    assert result.errors[0].code == "DFT_BELOW_MIN"


def test_dft_above_single_layer_limit_is_error():
    material = Material(material_name="Primer", max_single_layer_dft=150.0)
    result = TechnologyCheckService().check_dft(material, 160.0, layer_index=1)
    assert not result.passed
    assert any(i.code == "DFT_ABOVE_SINGLE_LAYER_MAX" for i in result.errors)


def test_recoat_too_early_is_error_and_too_late_is_warning():
    material = Material(material_name="Primer", min_recoat_time_h=4.0, max_recoat_time_h=24.0)
    early = TechnologyCheckService().check_recoat_interval(material, 2.0)
    late = TechnologyCheckService().check_recoat_interval(material, 30.0)
    assert not early.passed
    assert late.passed
    assert late.has_warnings


def test_total_dft_bounds_are_checked():
    service = TechnologyCheckService()
    low = service.check_total_dft(180.0, 200.0, 500.0)
    high = service.check_total_dft(520.0, 200.0, 500.0)
    assert not low.passed
    assert high.passed
    assert high.has_warnings
