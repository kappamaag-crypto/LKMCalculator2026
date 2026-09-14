from app.domain.chemical_resistance import ChemicalResistanceCheckResult, NOT_RESISTANT, RESISTANT, UNKNOWN
from app.domain.explanation import OK, UNKNOWN_DATA, WARNING, explain_engineering_bundle, explain_system_calculation
from app.domain.models import CoatingSystem, LayerResult, Material, ObjectData, SystemCalculationResult
from app.domain.pre_application import PreApplicationCheckResult


def _result(*, material: Material, losses_source: str = "DEFAULT", losses_percent: float = 0.0) -> SystemCalculationResult:
    layer = LayerResult(
        material=material,
        target_dft=120.0,
        losses_percent=losses_percent,
        losses_source=losses_source,
        losses_profile_name="profile-1" if losses_source == "PROFILE" else "",
        losses_note="test provenance" if losses_source == "EXPLICIT" else "",
        wft=150.0,
    )
    return SystemCalculationResult(
        system=CoatingSystem(system_name="Test system"),
        object_data=ObjectData(area_m2=10.0),
        layers=[layer],
        total_dft=120.0,
        total_cost_per_m2=None,
    )


def test_explanation_preserves_dft_basis_and_unknown_inputs() -> None:
    material = Material(material_name="Primer", density=1.4, solids_by_volume_percent=80.0)
    report = explain_system_calculation(_result(material=material))

    assert any(item.code == "LAYER_DFT_BASIS" and item.level == OK for item in report.items)
    assert any(item.code == "COST_UNKNOWN" and item.level == UNKNOWN_DATA for item in report.items)
    assert any(item.code == "CTX_SURFACE_UNKNOWN" and item.level == UNKNOWN_DATA for item in report.items)
    assert report.has_unknown_data()


def test_explanation_does_not_turn_missing_density_or_svb_into_zero() -> None:
    material = Material(material_name="Incomplete", density=None, solids_by_volume_percent=None)
    report = explain_system_calculation(_result(material=material))

    assert any(item.code == "LAYER_DENSITY_MISSING" for item in report.items)
    assert any(item.code == "LAYER_SV_MISSING" for item in report.items)
    assert not any("DFT=0" in item.message for item in report.items)


def test_explanation_reports_loss_provenance() -> None:
    material = Material(material_name="Primer", density=1.4, solids_by_volume_percent=80.0)

    explicit = explain_system_calculation(_result(material=material, losses_source="EXPLICIT", losses_percent=7.5))
    profile = explain_system_calculation(_result(material=material, losses_source="PROFILE", losses_percent=12.0))
    default = explain_system_calculation(_result(material=material, losses_source="DEFAULT", losses_percent=0.0))

    assert any(i.code == "LAYER_LOSSES_EXPLICIT" and "7.5 %" in i.message for i in explicit.items)
    assert any(i.code == "LAYER_LOSSES_PROFILE" and "profile=profile-1" in i.message for i in profile.items)
    assert any(i.code == "LAYER_LOSSES_ZERO" and "legacy default_losses" in i.message for i in default.items)


def test_explanation_bundle_carries_preapp_chem_and_recommendation_signals() -> None:
    material = Material(material_name="Primer", density=1.4, solids_by_volume_percent=80.0)
    pre_app = PreApplicationCheckResult()
    pre_app.add("PRE_DEW_POINT_UNKNOWN", "info", "Dew point is unknown.", scope="object", field="dew_point")

    chem = ChemicalResistanceCheckResult()
    chem.set_outcome("Primer", "acid", RESISTANT)
    chem.set_outcome("Primer", "alkali", NOT_RESISTANT)
    chem.set_outcome("Primer", "solvent", UNKNOWN)

    report = explain_engineering_bundle(
        _result(material=material),
        pre_app=pre_app,
        chem=chem,
        recommendation_reasons=["TDS-backed DFT"],
        recommendation_warnings=["Compatibility requires confirmation"],
        recommendation_limitations=["No source-backed chemical rule for one medium"],
    )

    codes = {item.code for item in report.items}
    assert "PREAPP_PRE_DEW_POINT_UNKNOWN" in codes
    assert "CHEM_RESISTANT" in codes
    assert "CHEM_NOT_RESISTANT" in codes
    assert "CHEM_UNKNOWN" in codes
    assert "REC_REASON_0" in codes
    assert "REC_WARN_0" in codes
    assert "REC_LIMIT_0" in codes
    assert report.overall_status == UNKNOWN_DATA
    assert any(item.level == WARNING and item.code == "CHEM_NOT_RESISTANT" for item in report.items)
