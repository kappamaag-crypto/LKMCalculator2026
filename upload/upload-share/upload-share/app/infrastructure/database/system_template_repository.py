"""Persistence gateway for confirmed System Templates."""
from __future__ import annotations

import json
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.system_template import SystemTemplateDraft, TemplateLayer
from app.infrastructure.database.system_template_models import SystemTemplateLayerORM, SystemTemplateORM


class SystemTemplateRepository:
    """Stores only explicitly confirmed templates; no catalogue auto-import is performed."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, template_id: int) -> Optional[SystemTemplateORM]:
        stmt = (
            select(SystemTemplateORM)
            .options(selectinload(SystemTemplateORM.layers))
            .where(SystemTemplateORM.id == template_id)
        )
        return self.session.scalar(stmt)

    def find_by_source(
        self,
        source_path: str,
        source_sheet: str,
        source_row: Optional[int],
        source_sha256: str,
    ) -> Optional[SystemTemplateORM]:
        stmt = (
            select(SystemTemplateORM)
            .where(
                SystemTemplateORM.source_path == source_path,
                SystemTemplateORM.source_sheet == source_sheet,
                SystemTemplateORM.source_sha256 == source_sha256,
            )
        )
        if source_row is None:
            stmt = stmt.where(SystemTemplateORM.source_row.is_(None))
        else:
            stmt = stmt.where(SystemTemplateORM.source_row == source_row)
        return self.session.scalar(stmt)

    def list_all(self, active_only: bool = True) -> Sequence[SystemTemplateORM]:
        stmt = (
            select(SystemTemplateORM)
            .options(selectinload(SystemTemplateORM.layers))
            .order_by(SystemTemplateORM.name)
        )
        if active_only:
            stmt = stmt.where(SystemTemplateORM.is_active.is_(True))
        return self.session.scalars(stmt).unique().all()

    def add_confirmed(self, draft: SystemTemplateDraft) -> SystemTemplateORM:
        draft.validate()
        if draft.status != "CONFIRMED":
            raise ValueError("В БД можно сохранить только CONFIRMED System Template")
        if draft.has_unknown_materials:
            raise ValueError("Нельзя сохранить шаблон с UNKNOWN материалом")
        if not draft.provenance_complete:
            raise ValueError("Нельзя сохранить шаблон без полной provenance")
        if self.find_by_source(
            draft.source_path, draft.source_sheet, draft.source_row, draft.source_sha256
        ) is not None:
            raise ValueError("Шаблон из этого источника уже сохранён")

        orm = SystemTemplateORM(
            name=draft.name,
            manufacturer=draft.manufacturer,
            description=draft.description,
            substrate=draft.substrate,
            source_path=draft.source_path,
            source_sheet=draft.source_sheet,
            source_row=draft.source_row,
            source_sha256=draft.source_sha256,
            status=draft.status,
            notes=draft.notes,
            metadata_json=json.dumps(draft.metadata, ensure_ascii=False, sort_keys=True),
            is_active=True,
        )
        for layer in draft.layers:
            if layer.material_id is None:
                raise ValueError(f"Слой {layer.layer_number}: material_id отсутствует")
            orm.layers.append(
                SystemTemplateLayerORM(
                    layer_number=layer.layer_number,
                    material_id=layer.material_id,
                    material_name=layer.material_name,
                    dft_min=layer.dft_min,
                    dft_target=layer.dft_target,
                    dft_max=layer.dft_max,
                    source_path=layer.source_path,
                    source_sheet=layer.source_sheet,
                    source_row=layer.source_row,
                    source_sha256=layer.source_sha256,
                )
            )
        self.session.add(orm)
        self.session.flush()
        return orm

    @staticmethod
    def to_draft(orm: SystemTemplateORM) -> SystemTemplateDraft:
        metadata = json.loads(orm.metadata_json or "{}")
        layers = tuple(
            TemplateLayer(
                layer_number=layer.layer_number,
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
            for layer in sorted(orm.layers, key=lambda item: item.layer_number)
        )
        return SystemTemplateDraft(
            name=orm.name,
            manufacturer=orm.manufacturer or "",
            description=orm.description or "",
            substrate=orm.substrate or "",
            source_path=orm.source_path,
            source_sheet=orm.source_sheet,
            source_row=orm.source_row,
            source_sha256=orm.source_sha256,
            layers=layers,
            notes=orm.notes or "",
            status=orm.status,
            metadata=metadata,
        )
