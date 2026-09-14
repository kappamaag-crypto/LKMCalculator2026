from app.domain.calculation_scenario import CalculationScenario
from app.domain.enums import BinderType, CompatibilityStatus, MaterialType
from app.domain.layer_compatibility import LayerCompatibilityReport, LayerDefinition, LayerTransitionResult
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.services.calculation_scenario_service import CalculationScenarioService


def material(name: str, binder: BinderType) -> Material:
    return Material(
        material_name=name,
        material_type=MaterialType.PRIMER,
        binder_type=binder,
        density=1.4,
        solids_by_volume_percent=70.0,
    )


def calculated_result(system: CoatingSystem) -> SystemCalculationResult:
    layers = [
        LayerResult(material=layer.material, target_dft=layer.target_dft or 100.0)
        for layer in system.layers
    ]
    return SystemCalculationResult(
        system=system,
        object_data=ObjectData(area_m2=100.0),
        layers=layers,
    )


class FakeCalculationService:
    def __init__(self, report: LayerCompatibilityReport):
        self.report = report

    def calculate_from_template(self, obj, system, materials_by_id, engineering_context=None):
        return calculated_result(system), type("Validation", (), {"has_errors": False, "errors": ()})()

    def compatibility_report(self, result):
        return self.report


def test_scenario_retains_compatibility_report_for_each_alternative():
    primer = material("Epoxy primer", BinderType.EPOXY)
    finish = material("PU finish", BinderType.POLYURETHANE)
    system = CoatingSystem(
        system_name="System A",
        number_of_layers=2,
        layers=[
            LayerDefinition(material_id=1, material=primer, layer_number=1, target_dft=100.0),
            LayerDefinition(material_id=2, material=finish, layer_number=2, target_dft=80.0),
        ],
    )
    result = calculated_result(system)
    transition = LayerTransitionResult(
        previous_layer_index=1,
        applied_layer_index=2,
        previous_material=primer,
        applied_material=finish,
        rule=__import__("app.domain.compatibility", fromlist=["CompatibilityRule"]).CompatibilityRule(
            previous_family="epoxy",
            applied_family="polyurethane",
            status=CompatibilityStatus.WARNING,
            note="Требуется придание шероховатости",
        ),
    )
    report = LayerCompatibilityReport(transitions=(transition,))
    service = CalculationScenarioService(FakeCalculationService(report))

    scenario = CalculationScenario(
        name="Scenario A",
        object_data=result.object_data,
        alternatives=(system,),
    )

    evaluated = service.evaluate(scenario)

    assert len(evaluated.alternatives) == 1
    assert evaluated.alternatives[0].result is not None
    assert evaluated.alternatives[0].compatibility is report
    assert evaluated.alternatives[0].compatibility.status is CompatibilityStatus.WARNING
