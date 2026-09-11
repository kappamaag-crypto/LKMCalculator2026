from app.domain.enums import MaterialType
from app.domain.models import CoatingSystem, LayerDefinition, Material
from app.services.calculation_service import CalculationService

def test_check_system_tds_dft_and_trace():
    mat = Material(material_name="Blank Finish topcoat", material_type=MaterialType.ENAMEL, manufacturer="Blank")
    system = CoatingSystem(
        system_name="S",
        layers=[LayerDefinition(material=mat, layer_number=1, target_dft=70)],
    )
    svc = CalculationService()
    checks = svc.check_system_tds_dft(system)
    assert len(checks) == 1
    assert any(i.code == "TECH_TDS_DFT_OK" for i in checks[0][1].issues)
    traces = svc.tds_trace_for_system(system)
    assert traces[0]["tds_verified"] == "KNOWN"
    ctx = svc.build_tds_engineering_context(system)
    assert ctx.normative_status == "KNOWN"
