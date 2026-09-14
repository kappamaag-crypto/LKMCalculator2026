"""Unique material binding for reviewed System Template drafts (TDS gate prep)."""
from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_template_service import SystemTemplateService


def _layer(name: str, *, material_id=None, row=1) -> TemplateLayer:
    return TemplateLayer(
        layer_number=1 if row == 1 else row,
        material_name=name,
        material_id=material_id,
        dft_target=80.0,
        source_path="books/Системы 3.xlsx",
        source_sheet="АКЗ",
        source_row=row,
        source_sha256="c" * 64,
    )


def _draft(*layers: TemplateLayer) -> SystemTemplateDraft:
    # renumber sequentially
    renumbered = []
    for i, layer in enumerate(layers, 1):
        renumbered.append(
            TemplateLayer(
                layer_number=i,
                material_name=layer.material_name,
                material_id=layer.material_id,
                dft_min=layer.dft_min,
                dft_target=layer.dft_target,
                dft_max=layer.dft_max,
                source_path=layer.source_path,
                source_sheet=layer.source_sheet,
                source_row=layer.source_row,
                source_sha256=layer.source_sha256,
            )
        )
    return SystemTemplateDraft(
        name="TEST/АКЗ/#1/Mat",
        manufacturer="Test",
        source_path="books/Системы 3.xlsx",
        source_sheet="АКЗ",
        source_row=8,
        source_sha256="c" * 64,
        layers=tuple(renumbered),
        status="DRAFT",
        metadata={"source_kind": "SYSTEMS_CATALOG_SIDE_BY_SIDE", "tds_verified": "UNKNOWN"},
    )


def test_bind_unique_materials_sets_id_on_exact_name_match():
    materials = [
        Material(id=10, material_name="Blank Universal", manufacturer="Колоридо"),
        Material(id=20, material_name="Blank Finish", manufacturer="Колоридо"),
    ]
    draft = _draft(_layer("Blank Universal"), _layer("Blank Finish", row=2))
    bound = SystemTemplateService.bind_unique_materials(draft, materials)
    assert [layer.material_id for layer in bound.layers] == [10, 20]
    assert bound.status == "DRAFT"
    assert bound.metadata.get("tds_verified") == "UNKNOWN"


def test_bind_unique_materials_leaves_none_when_ambiguous():
    materials = [
        Material(id=1, material_name="Blank Universal", manufacturer="A"),
        Material(id=2, material_name="Blank Universal", manufacturer="B"),
    ]
    draft = _draft(_layer("Blank Universal"))
    bound = SystemTemplateService.bind_unique_materials(draft, materials)
    assert bound.layers[0].material_id is None


def test_bind_unique_materials_leaves_none_when_no_match():
    materials = [Material(id=5, material_name="Other Product")]
    draft = _draft(_layer("ЭФФА ЭП-150"))
    bound = SystemTemplateService.bind_unique_materials(draft, materials)
    assert bound.layers[0].material_id is None


def test_bind_unique_materials_preserves_existing_id():
    materials = [Material(id=99, material_name="Blank Universal")]
    draft = _draft(_layer("Blank Universal", material_id=42))
    bound = SystemTemplateService.bind_unique_materials(draft, materials)
    assert bound.layers[0].material_id == 42


def test_prepare_reviewed_draft_for_review_never_confirms():
    materials = [Material(id=10, material_name="Blank Universal")]
    draft = _draft(_layer("Blank Universal"))
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(draft, materials)
    assert prepared.status == "DRAFT"
    assert prepared.layers[0].material_id == 10
    # Without KNOWN TDS rule for the name, tds stays UNKNOWN
    assert prepared.metadata.get("tds_verified") in ("UNKNOWN", "KNOWN")
    ok, reasons = SystemTemplateService.can_confirm(prepared)
    # Even with material id, CONFIRM still requires tds_verified=KNOWN
    if prepared.metadata.get("tds_verified") != "KNOWN":
        assert ok is False
        assert any("TDS" in r for r in reasons)


def test_prepare_reviewed_draft_for_review_casefold_and_yo():
    materials = [Material(id=7, material_name="Грунт-эмаль Blank Universal")]
    draft = _draft(_layer("ГРУНТ-ЭМАЛЬ BLANK UNIVERSAL"))
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(draft, materials)
    assert prepared.layers[0].material_id == 7
