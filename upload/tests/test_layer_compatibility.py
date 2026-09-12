from app.domain.enums import BinderType, CompatibilityStatus, MaterialType
from app.domain.layer_compatibility import LayerCompatibilityContext, LayerCompatibilityEngine
from app.domain.models import CoatingSystem, LayerDefinition, LayerResult, Material, ObjectData, SystemCalculationResult
from app.services.calculation_service import CalculationService


def material(name: str, binder: BinderType) -> Material:
    return Material(
        material_name=name,
        material_type=MaterialType.PRIMER,
        binder_type=binder,
        density=1.4,
        solids_by_volume_percent=70.0,
    )


def test_engine_checks_every_adjacent_transition_in_a_four_layer_system():
    layers = [
        LayerDefinition(material=material("Epoxy primer", BinderType.EPOXY)),
        LayerDefinition(material=material("Epoxy intermediate", BinderType.EPOXY)),
        LayerDefinition(material=material("Acrylic intermediate", BinderType.ACRYLIC)),
        LayerDefinition(material=material("Acrylic finish", BinderType.ACRYLIC)),
    ]

    report = LayerCompatibilityEngine().check_layers(layers)

    assert len(report.transitions) == 3
    assert [item.previous_layer_index for item in report.transitions] == [1, 2, 3]
    assert [item.applied_layer_index for item in report.transitions] == [2, 3, 4]
    # Source matrix: epoxy→epoxy = WARNING (roughness); epoxy→acrylic = ALLOWED; acrylic→acrylic = UNKNOWN
    assert report.transitions[0].status is CompatibilityStatus.WARNING
    assert report.transitions[1].status is CompatibilityStatus.ALLOWED
    assert report.transitions[2].status is CompatibilityStatus.UNKNOWN
    assert report.status is CompatibilityStatus.UNKNOWN


def test_engine_preserves_source_warning_and_explains_the_transition():
    previous = material("Epoxy primer", BinderType.EPOXY)
    applied = material("PU finish", BinderType.POLYURETHANE)

    report = LayerCompatibilityEngine().check_material_sequence([previous, applied])

    assert report.status is CompatibilityStatus.WARNING
    assert report.transitions[0].rule.note == "Требуется придание шероховатости"
    assert "Слой 2" in report.transitions[0].message
    assert "PU finish" in report.transitions[0].message


def test_engine_returns_unknown_for_unmapped_binder_without_inventing_a_rule():
    previous = material("Unknown primer", BinderType.ALKYD)
    applied = material("Epoxy finish", BinderType.EPOXY)

    report = LayerCompatibilityEngine().check_material_sequence([previous, applied])

    assert report.status is CompatibilityStatus.UNKNOWN
    assert report.transitions[0].rule.previous_family == "unknown"
    assert report.transitions[0].rule.applied_family == "epoxy"
    assert report.transitions[0].rule.source


def test_engine_worst_case_is_unknown_when_one_transition_is_unresolved():
    materials = [
        material("Epoxy primer", BinderType.EPOXY),
        material("Epoxy intermediate", BinderType.EPOXY),
        material("Alkyd material", BinderType.ALKYD),
    ]
    contexts = [
        LayerCompatibilityContext(previous_is_cured=True),
        LayerCompatibilityContext(previous_is_cured=False),
    ]

    report = LayerCompatibilityEngine().check_material_sequence(materials, contexts)

    assert len(report.transitions) == 2
    # epoxy→epoxy remains WARNING even when previous_is_cured=True (source matrix)
    assert report.transitions[0].status is CompatibilityStatus.WARNING
    assert report.transitions[0].context.previous_is_cured is True
    assert report.transitions[1].status is CompatibilityStatus.UNKNOWN
    assert report.status is CompatibilityStatus.UNKNOWN
    assert len(report.blocking_transitions) == 1


def test_engine_checks_system_calculation_result_without_recalculation():
    layers = [
        LayerResult(material=material("Epoxy primer", BinderType.EPOXY), target_dft=100.0),
        LayerResult(material=material("PU finish", BinderType.POLYURETHANE), target_dft=80.0),
    ]
    result = SystemCalculationResult(
        system=CoatingSystem(number_of_layers=2),
        object_data=ObjectData(area_m2=100.0),
        layers=layers,
    )

    report = LayerCompatibilityEngine().check_result(result)

    assert len(report.transitions) == 1
    assert report.transitions[0].previous_material is layers[0].material
    assert report.transitions[0].applied_material is layers[1].material
    assert report.status is CompatibilityStatus.WARNING


def test_calculation_service_exposes_compatibility_report_for_existing_result():
    layers = [
        LayerResult(material=material("Epoxy primer", BinderType.EPOXY), target_dft=100.0),
        LayerResult(material=material("PU finish", BinderType.POLYURETHANE), target_dft=80.0),
    ]
    result = SystemCalculationResult(
        system=CoatingSystem(number_of_layers=2),
        object_data=ObjectData(area_m2=100.0),
        layers=layers,
    )

    report = CalculationService().compatibility_report(result)

    assert report.status is CompatibilityStatus.WARNING
    assert len(report.warning_transitions) == 1


def test_engine_requires_one_context_per_transition():
    layers = [
        LayerDefinition(material=material("Epoxy primer", BinderType.EPOXY)),
        LayerDefinition(material=material("PU finish", BinderType.POLYURETHANE)),
        LayerDefinition(material=material("Acrylic finish", BinderType.ACRYLIC)),
    ]

    try:
        LayerCompatibilityEngine().check_layers(layers, [LayerCompatibilityContext()])
    except ValueError as exc:
        assert "exactly one item" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid context count")
