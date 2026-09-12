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


def test_prepare_keeps_unbound_when_material_match_is_ambiguous():
    materials = [
        Material(id=7, material_name="Blank Universal"),
        Material(id=8, material_name="Blank Universal"),
    ]
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(
        _draft(), materials
    )

    # Ambiguous DB match → no material_id. TDS may still be KNOWN from name rule.
    assert prepared.layers[0].material_id is None
    ok, reasons = SystemTemplateService.can_confirm(prepared)
    assert not ok
    assert any("однозначного сопоставления" in reason for reason in reasons)


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


def test_confirm_draft_succeeds_when_all_gates_pass():
    material = Material(id=7, manufacturer="ООО Колоридо", material_name="Blank Universal")
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(_draft(), [material])
    assert prepared.metadata["tds_verified"] == "KNOWN"
    confirmed = SystemTemplateService.confirm_draft(prepared)
    assert confirmed.status == "CONFIRMED"
    assert confirmed.layers[0].material_id == 7
    assert confirmed.metadata["tds_verified"] == "KNOWN"
    # confirm is idempotent gate on already-valid input; can_confirm still true
    assert SystemTemplateService.can_confirm(confirmed) == (True, ())


def test_confirm_draft_rejects_unknown_tds():
    draft = _draft(material_id=7, tds="UNKNOWN")
    try:
        SystemTemplateService.confirm_draft(draft)
    except ValueError as exc:
        assert "CONFIRM запрещён" in str(exc)
        assert "TDS" in str(exc)
    else:
        raise AssertionError("confirm_draft must reject UNKNOWN TDS")


def test_confirm_draft_rejects_unbound_material():
    draft = _draft(material_id=None, tds="KNOWN")
    try:
        SystemTemplateService.confirm_draft(draft)
    except ValueError as exc:
        assert "CONFIRM запрещён" in str(exc)
        assert "сопоставления" in str(exc)
    else:
        raise AssertionError("confirm_draft must reject unbound material")


def test_confirm_draft_never_auto_runs_from_prepare_alone():
    material = Material(id=7, material_name="Blank Universal")
    prepared = SystemTemplateService.prepare_reviewed_draft_for_review(_draft(), [material])
    assert prepared.status == "DRAFT"
    assert prepared.status != "CONFIRMED"
