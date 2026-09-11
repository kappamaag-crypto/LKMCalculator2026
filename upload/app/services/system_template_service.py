"""Build reviewed System Template drafts from catalogue staging records."""
from __future__ import annotations
from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_catalog_importer import SystemRowCandidate

class SystemTemplateService:
    """Create drafts only; persistence belongs to an explicit later workflow."""

    @staticmethod
    def build_draft(row: SystemRowCandidate, materials: list[Material]) -> SystemTemplateDraft:
        material_map: dict[str, list[Material]] = {}
        for material in materials:
            material_map.setdefault(material.material_name.strip().casefold(), []).append(material)
            material_map.setdefault(material.display_name().strip().casefold(), []).append(material)

        layers: list[TemplateLayer] = []
        for number, candidate in enumerate(row.material_candidates, 1):
            matches = material_map.get(candidate.name.strip().casefold(), [])
            material_id = matches[0].id if len(matches) == 1 else None
            layers.append(TemplateLayer(
                layer_number=number,
                material_name=candidate.name or "UNKNOWN",
                material_id=material_id,
                source_path=candidate.source_path,
                source_sheet=candidate.sheet,
                source_row=candidate.row_number,
                source_sha256=candidate.source_sha256,
            ))

        system_name = "UNKNOWN"
        for key, value in row.values:
            key_norm = key.casefold().replace("ё", "е")
            if any(token in key_norm for token in ("система", "марка", "обозначение", "system")):
                system_name = value or "UNKNOWN"
                break

        draft = SystemTemplateDraft(
            name=system_name,
            source_path=row.source_path,
            source_sheet=row.sheet,
            source_row=row.row_number,
            source_sha256=row.source_sha256,
            layers=tuple(layers),
            status="DRAFT",
            metadata={"source_kind": "system_catalogue", "tds_verified": "UNKNOWN"},
        )
        draft.validate()
        return draft

    @staticmethod
    def can_confirm(draft: SystemTemplateDraft) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        if draft.has_unknown_materials:
            reasons.append("Есть материал без однозначного сопоставления с БД")
        if not draft.provenance_complete:
            reasons.append("Неполная provenance цепочка источника")
        if draft.metadata.get("tds_verified") != "KNOWN":
            reasons.append("TDS применимости ещё не подтверждены")
        return not reasons, tuple(reasons)
