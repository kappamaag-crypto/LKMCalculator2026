from app.domain.enums import CorrosionCategory, DurabilityLevel, MaterialType
from app.domain.models import CoatingSystem, LayerDefinition, Material, ObjectData
from app.domain.recommendation.rules import filter_system


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
        "corrosion_category": CorrosionCategory.C3,
        "durability": DurabilityLevel.MEDIUM,
        "surface_temperature": 20,
        "air_temperature": 20,
        "relative_humidity": 60,
        "dew_point": 15,
    }
    values.update(kwargs)
    return ObjectData(**values)


def make_system(material, target_dft=120):
    return CoatingSystem(
        system_name="Test system",
        corrosion_categories=[CorrosionCategory.C3],
        durability=DurabilityLevel.MEDIUM,
        layers=[LayerDefinition(material=material, layer_number=1, target_dft=target_dft)],
    )


def test_dew_point_violation_blocks_recommendation_filter():
    result = filter_system(
        make_system(make_material()),
        make_object(surface_temperature=17, dew_point=15),
    )
    assert not result.passed
    assert any("TECH_DEW_POINT_MARGIN" not in reason for reason in [])
    assert any("Запас до точки росы" in reason for reason in result.reasons_fail)


def test_valid_technology_conditions_pass_filter():
    result = filter_system(make_system(make_material()), make_object())
    assert result.passed
    assert not result.reasons_fail


def test_target_dft_above_absolute_limit_blocks_filter():
    result = filter_system(
        make_system(make_material(), target_dft=300),
        make_object(),
    )
    assert not result.passed
    assert any("абсолютного максимума" in reason for reason in result.reasons_fail)


def test_missing_material_is_insufficient_data_not_zero():
    system = make_system(None)
    result = filter_system(system, make_object())
    assert not result.passed
    assert result.insufficient_data
    assert any("материал не загружен" in reason for reason in result.reasons_fail)
