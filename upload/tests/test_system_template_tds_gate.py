from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_template_service import SystemTemplateService


def _draft(*, material_id=None, material_name="Blank Universal", source=True, tds="UNKNOWN"):
    source_path = "books/Системы 2.XLSX" if source else ""
    source_sha256 = "a" * 64 if source else ""
    return SystemTemplateDraft(
        name="Система test",
        source_path=source_path,
        source_sheet="АКЗ",
        source_row=8,
        source_sha256=source_sha256,
        layers=(
            TemplateLayer(
                layer_number=1,
                material_name=material_name,
                material_id=material_id,
                dft_target=100.0,
                source_path=source_path,
                source_sheet="АКЗ",
                source_row=8,
                source_sha256=source_sha256,
            ),
        ),
        status="DRAFT",
        metadata={"tds_verified": tds},
    )


def test_prepare_binds_unique_material_and_promotes_tds_status_to_known():
    material = Material(id=7, manufacturer="ООО Колоридо", material_name="Blank Universal")
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(
        _draft(), [material]
    )

    assert prepared.status == "DRAFT"
    assert prepared.layers[0].material_id == 7
    assert prepared.metadata["tds_verified"] == "KNOWN"
    assert SystemTemplateService.can_confirm(prepared) == (True, ())


def test_prepare_keeps_unknown_when_material_match_is_ambiguous():
    materials = [
        Material(id=7, material_name="Blank Universal"),
        Material(id=8, material_name="Blank Universal"),
    ]
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(
        _draft(), materials
    )

    assert prepared.layers[0].material_id is None
    assert prepared.metadata["tds_verified"] == "UNKNOWN"
    ok, reasons = SystemTemplateService.can_confirm(prepared)
    assert not ok
    assert any("однозначного сопоставления" in reason for reason in reasons)
    assert any("TDS" in reason for reason in reasons)


def test_can_confirm_rejects_missing_provenance_even_with_known_tds():
    draft = _draft(source=False, tds="KNOWN")
    draft = SystemTemplateDraft(
        name=draft.name,
        source_path=draft.source_path,
        source_sheet=draft.source_sheet,
        source_row=draft.source_row,
        source_sha256=draft.source_sha256,
        layers=draft.layers,
        status="REVIEW",
        metadata={"tds_verified": "KNOWN"},
    )

    ok, reasons = SystemTemplateService.can_confirm(draft)

    assert not ok
    assert any("provenance" in reason.lower() for reason in reasons)


def test_can_confirm_requires_known_tds_even_when_material_and_provenance_are_valid():
    material = Material(id=7, material_name="Blank Universal")
    draft = _draft(material_id=7, tds="UNKNOWN")
    ok, reasons = SystemTemplateService.can_confirm(draft)

    assert not ok
    assert reasons == ("TDS применимости ещё не подтверждены",)
    assert material.id == draft.layers[0].material_id
