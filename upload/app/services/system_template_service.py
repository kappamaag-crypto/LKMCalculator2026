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
    def _material_index(materials: Sequence[Material] | None) -> dict[str, list[Material]]:
        """Map casefolded names to materials; empty/missing names skipped."""
        index: dict[str, list[Material]] = {}
        if not materials:
            return index
        for material in materials:
            for key in (
                getattr(material, "material_name", None),
                material.display_name() if hasattr(material, "display_name") else None,
            ):
                if not key:
                    continue
                norm = str(key).strip().casefold().replace("ё", "е")
                if not norm:
                    continue
                index.setdefault(norm, []).append(material)
        return index

    @staticmethod
    def bind_unique_materials(
        draft: SystemTemplateDraft,
        materials: Sequence[Material] | None,
    ) -> SystemTemplateDraft:
        """Attach material_id only when the layer name uniquely matches the catalogue.

        Ambiguous or missing matches leave material_id=None (UNKNOWN binding).
        Does not change status and does not invent TDS verification.
        """
        index = SystemTemplateService._material_index(materials)
        layers: list[TemplateLayer] = []
        for layer in draft.layers:
            if layer.material_id is not None:
                layers.append(layer)
                continue
            norm = (layer.material_name or "").strip().casefold().replace("ё", "е")
            matches = index.get(norm, [])
            # Unique by id among name hits
            unique: dict[int, Material] = {}
            for material in matches:
                mid = getattr(material, "id", None)
                if mid is None:
                    continue
                unique[mid] = material
            if len(unique) == 1:
                material = next(iter(unique.values()))
                layers.append(
                    TemplateLayer(
                        layer_number=layer.layer_number,
                        material_name=layer.material_name,
                        material_id=material.id,
                        dft_min=layer.dft_min,
                        dft_target=layer.dft_target,
                        dft_max=layer.dft_max,
                        source_path=layer.source_path,
                        source_sheet=layer.source_sheet,
                        source_row=layer.source_row,
                        source_sha256=layer.source_sha256,
                    )
                )
            else:
                layers.append(layer)
        return SystemTemplateDraft(
            name=draft.name,
            manufacturer=draft.manufacturer,
            description=draft.description,
            substrate=draft.substrate,
            source_path=draft.source_path,
            source_sheet=draft.source_sheet,
            source_row=draft.source_row,
            source_sha256=draft.source_sha256,
            layers=tuple(layers),
            notes=draft.notes,
            status=draft.status,
            metadata=dict(draft.metadata),
        )

    @staticmethod
    def prepare_reviewed_draft_for_review(
        draft: SystemTemplateDraft,
        materials: Sequence[Material] | None = None,
    ) -> SystemTemplateDraft:
        """TDS-gate preparation: unique material bind, then re-evaluate tds_verified.

        Status stays DRAFT/REVIEW as provided — never auto-CONFIRMED.
        """
        bound = SystemTemplateService.bind_unique_materials(draft, materials)
        return SystemTemplateService.with_tds_verification(bound, materials)

    @staticmethod
    def can_confirm(draft):
        reasons = []
        if draft.has_unknown_materials: reasons.append("Есть материал без однозначного сопоставления с БД")
        if not draft.provenance_complete: reasons.append("Неполная provenance цепочка источника")
        if draft.metadata.get("tds_verified") != "KNOWN": reasons.append("TDS применимости ещё не подтверждены")
        return not reasons, tuple(reasons)

    @staticmethod
    def confirm_draft(draft: SystemTemplateDraft) -> SystemTemplateDraft:
        """Explicit CONFIRM gate after review.

        Requires can_confirm (unique materials, full provenance, tds_verified=KNOWN).
        Does not persist and does not invent material bindings or TDS status.
        """
        draft.validate()
        ok, reasons = SystemTemplateService.can_confirm(draft)
        if not ok:
            raise ValueError("CONFIRM запрещён: " + "; ".join(reasons))
        confirmed = SystemTemplateDraft(
            name=draft.name,
            manufacturer=draft.manufacturer,
            description=draft.description,
            substrate=draft.substrate,
            source_path=draft.source_path,
            source_sheet=draft.source_sheet,
            source_row=draft.source_row,
            source_sha256=draft.source_sha256,
            layers=draft.layers,
            notes=draft.notes,
            status="CONFIRMED",
            metadata=dict(draft.metadata),
        )
        confirmed.validate()
        return confirmed
