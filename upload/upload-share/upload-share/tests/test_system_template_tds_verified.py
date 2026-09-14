from app.domain.enums import MaterialType
from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_template_service import SystemTemplateService

def _mat(mid, name):
    return Material(id=mid, material_name=name, material_type=MaterialType.PRIMER, manufacturer="Blank", brand="Blank")
def _layer(n, name, mid):
    return TemplateLayer(layer_number=n, material_name=name, material_id=mid, dft_target=100.0,
        source_path="b.xlsx", source_sheet="S", source_row=n, source_sha256="a"*64)
def _draft(layers):
    return SystemTemplateDraft(name="T", source_path="b.xlsx", source_sheet="S", source_row=1, source_sha256="b"*64,
        layers=tuple(layers), status="REVIEW", metadata={"source_kind": "system_catalogue", "tds_verified": "UNKNOWN"})

def test_evaluate_known():
    assert SystemTemplateService.evaluate_tds_verified(_draft([_layer(1, "Blank Universal primer", 1)]), [_mat(1, "Blank Universal primer")])[0] == "KNOWN"
def test_with_tds_metadata():
    u = SystemTemplateService.with_tds_verification(_draft([_layer(1, "Blank Tank LP", 2)]), [_mat(2, "Blank Tank LP")])
    assert u.metadata["tds_verified"] == "KNOWN"
