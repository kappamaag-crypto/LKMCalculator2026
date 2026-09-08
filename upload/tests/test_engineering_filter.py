from app.domain.enums import CorrosionCategory, DurabilityLevel, ApplicationMethod, SurfaceType
from app.domain.models import CoatingSystem, ObjectData, Material, LayerDefinition
from app.domain.recommendation.engineering_filter import evaluate_system


def make_system(**kwargs):
    material = Material(
        material_name="Test primer",
        recommended_dft_min=60,
        recommended_dft_max=120,
        max_single_layer_dft=150,
        min_application_temperature=5,
        max_application_temperature=40,
        max_relative_humidity=80,
        min_dew_point_margin_c=3,
        application_method=ApplicationMethod.AIRLESS,
    )
    layer = LayerDefinition(material=material, target_dft=80)
    return CoatingSystem(
        system_name="Test system",
        corrosion_categories=[CorrosionCategory.C4],
        durability=DurabilityLevel.HIGH,
        surface_types=[SurfaceType.NEW_STEEL],
        number_of_layers=1,
        layers=[layer],
        total_dft_min=70,
        total_dft_target=80,
        total_dft_max=120,
        **kwargs,
    )


def make_object(**kwargs):
    return ObjectData(
        corrosion_category=CorrosionCategory.C4,
        durability=DurabilityLevel.MEDIUM,
        surface_type=SurfaceType.NEW_STEEL,
        surface_temperature=20,
        dew_point=15,
        relative_humidity=60,
        application_method=ApplicationMethod.AIRLESS,
        **kwargs,
    )


def test_compliant_system_passes():
    result = evaluate_system(make_system(), make_object())
    assert result.status == "Подходит"
    assert result.passed
    assert not result.failed_checks


def test_missing_critical_system_data_is_not_treated_as_pass():
    system = make_system(corrosion_categories=[])
    result = evaluate_system(system, make_object())
    assert result.status == "Недостаточно данных"
    assert result.has_insufficient_data


def test_wrong_category_is_rejected():
    system = make_system(corrosion_categories=[CorrosionCategory.C3])
    result = evaluate_system(system, make_object())
    assert result.status == "Не подходит"
    assert result.failed_checks


def test_bad_dew_point_margin_is_rejected():
    result = evaluate_system(make_system(), make_object(surface_temperature=17, dew_point=15))
    assert result.status == "Не подходит"
    assert any("точки росы" in msg for msg in result.failed_checks)


def test_excessive_single_layer_dft_is_rejected():
    system = make_system()
    system.layers[0].target_dft = 200
    result = evaluate_system(system, make_object())
    assert result.status == "Не подходит"
    assert any("абсолютного максимума" in msg for msg in result.failed_checks)
