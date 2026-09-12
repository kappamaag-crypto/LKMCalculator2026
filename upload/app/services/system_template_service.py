"""Build reviewed System Template drafts from catalogue staging records."""
from __future__ import annotations
from pathlib import Path
from typing import Mapping, Sequence
from app.domain.models import Material
from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.services.system_catalog_importer import SystemRowCandidate
from app.services.tds_known_rules import known_dft_rule_for_material_name

class SystemTemplateService:
    @staticmethod
    def build_draft(row: SystemRowCandidate, materials: list[Material]) -> SystemTemplateDraft:
        material_map = {}
        for material in materials:
            material_map.setdefault(material.material_name.strip().casefold(), []).append(material)
            material_map.setdefault(material.display_name().strip().casefold(), []).append(material)
        layers = []
        for number, candidate in enumerate(row.material_candidates, 1):
            matches = material_map.get(candidate.name.strip().casefold(), [])
            material_id = matches[0].id if len(matches) == 1 else None
            layers.append(TemplateLayer(layer_number=number, material_name=candidate.name or "UNKNOWN",
                material_id=material_id, source_path=candidate.source_path, source_sheet=candidate.sheet,
                source_row=candidate.row_number, source_sha256=candidate.source_sha256))
        system_name = "UNKNOWN"
        for key, value in row.values:
            key_norm = key.casefold().replace("ё", "е")
            if any(token in key_norm for token in ("система", "марка", "обозначение", "system")):
                system_name = value or "UNKNOWN"; break
        draft = SystemTemplateDraft(name=system_name, source_path=row.source_path, source_sheet=row.sheet,
            source_row=row.row_number, source_sha256=row.source_sha256, layers=tuple(layers), status="DRAFT",
            metadata={"source_kind": "system_catalogue", "tds_verified": "UNKNOWN"})
        draft.validate(); return draft

    @staticmethod
    def evaluate_tds_verified(draft, materials=None):
        by_id = {}
        if materials is not None:
            if isinstance(materials, Mapping): by_id = dict(materials)
            else:
                for m in materials:
                    if getattr(m, "id", None) is not None: by_id[m.id] = m
        reasons = []
        if not draft.layers: return "UNKNOWN", ("Нет слоёв для TDS-проверки",)
        for layer in draft.layers:
            name = layer.material_name
            if layer.material_id is not None and layer.material_id in by_id:
                mat = by_id[layer.material_id]
                name = mat.material_name or mat.display_name() or name
            rule = known_dft_rule_for_material_name(name or "")
            if rule is None or rule.status != "KNOWN":
                reasons.append(f"Слой {layer.layer_number}: нет KNOWN TDS DFT-правила для «{name or 'UNKNOWN'}»")
        return ("UNKNOWN", tuple(reasons)) if reasons else ("KNOWN", ())

    @staticmethod
    def with_tds_verification(draft, materials=None):
        status, _ = SystemTemplateService.evaluate_tds_verified(draft, materials)
        meta = dict(draft.metadata); meta["tds_verified"] = status
        return SystemTemplateDraft(name=draft.name, manufacturer=draft.manufacturer, description=draft.description,
            substrate=draft.substrate, source_path=draft.source_path, source_sheet=draft.source_sheet,
            source_row=draft.source_row, source_sha256=draft.source_sha256, layers=draft.layers,
            notes=draft.notes, status=draft.status, metadata=meta)

    @staticmethod
    def load_reviewed_side_by_side_drafts(
        books_root: str | Path,
        *,
        file_names: Sequence[str] | None = None,
    ) -> tuple[SystemTemplateDraft, ...]:
        """Load DRAFT templates from workbooks that have reviewed side-by-side layouts.

        Only files/sheets present in ``REVIEWED_SIDE_BY_SIDE_LAYOUTS`` are expanded.
        Status remains DRAFT; ``tds_verified`` stays UNKNOWN until explicit review.
        Does not persist and does not auto-CONFIRM.
        """
        from app.services.system_book_mapping import (
            REVIEWED_SIDE_BY_SIDE_LAYOUTS,
            expand_reviewed_workbook,
        )

        root = Path(books_root)
        names = (
            list(file_names)
            if file_names is not None
            else sorted({key[0] for key in REVIEWED_SIDE_BY_SIDE_LAYOUTS})
        )
        drafts: list[SystemTemplateDraft] = []
        for name in names:
            path = root / name
            if not path.is_file():
                continue
            drafts.extend(expand_reviewed_workbook(path))
        return tuple(drafts)

    @staticmethod
    def can_confirm(draft):
        reasons = []
        if draft.has_unknown_materials: reasons.append("Есть материал без однозначного сопоставления с БД")
        if not draft.provenance_complete: reasons.append("Неполная provenance цепочка источника")
        if draft.metadata.get("tds_verified") != "KNOWN": reasons.append("TDS применимости ещё не подтверждены")
        return not reasons, tuple(reasons)
