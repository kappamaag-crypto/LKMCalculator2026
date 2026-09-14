from app.domain.enums import MaterialType
from app.domain.models import Material, ObjectData
from app.domain.technology import check_application_technology


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
        "dew_point": 15,
    }
    values.update(kwargs)
    return ObjectData(**values)


def test_dew_point_margin_is_blocking():
    result = check_application_technology(make_object(surface_temperature=17, dew_point=15), make_material())
    assert result.blocking
    assert any(issue.code == "TECH_DEW_POINT_MARGIN" for issue in result.issues)


def test_dft_below_min_is_blocking():
    result = check_application_technology(make_object(), make_material(), actual_dft=70)
    assert result.blocking
    assert any(issue.code == "TECH_DFT_BELOW_MIN" for issue in result.issues)


def test_dft_above_recommended_but_below_absolute_max_is_warning():
    result = check_application_technology(make_object(), make_material(), actual_dft=220)
    assert not result.blocking
    assert result.has_warnings
    assert any(issue.code == "TECH_DFT_ABOVE_RECOMMENDED" for issue in result.issues)


def test_missing_dft_is_unknown_not_zero():
    result = check_application_technology(make_object(), make_material())
    assert not any(issue.code == "TECH_DFT_BELOW_MIN" for issue in result.issues)
    assert any(issue.code == "TECH_DFT_UNKNOWN" for issue in result.issues)
