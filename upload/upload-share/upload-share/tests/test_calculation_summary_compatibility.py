from app.domain.enums import BinderType, CompatibilityStatus, MaterialType
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.services.calculation_service import CalculationService


def material(name: str, binder: BinderType) -> Material:
    return Material(
        material_name=name,
        material_type=MaterialType.PRIMER,
        binder_type=binder,
        density=1.4,
        solids_by_volume_percent=70.0,
    )


def test_calculation_summary_reports_source_backed_layer_compatibility():
    primer = material("Epoxy primer", BinderType.EPOXY)
    finish = material("PU finish", BinderType.POLYURETHANE)
    result = SystemCalculationResult(
        system=CoatingSystem(system_name="Demo system", number_of_layers=2),
        object_data=ObjectData(area_m2=10.0),
        layers=[
            LayerResult(material=primer, target_dft=100.0),
            LayerResult(material=finish, target_dft=80.0),
        ],
    )

    service = CalculationService()
    report = service.compatibility_report(result)
    text = service.format_summary(result)

    assert report.status is CompatibilityStatus.WARNING
    assert "Совместимость слоёв: ПРЕДУПРЕЖДЕНИЕ" in text
    assert "Требуется придание шероховатости" in text
    assert "https://www.lkm-prof.ru/razdel/sovmestim.php" in text
