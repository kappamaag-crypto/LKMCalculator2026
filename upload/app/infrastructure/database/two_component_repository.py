"""Репозиторий справочных данных 2К-материалов."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import MaterialComponent, MaterialMix
from app.infrastructure.database.models import MaterialComponentORM, MaterialMixORM


def _component_to_domain(row: MaterialComponentORM) -> MaterialComponent:
    return MaterialComponent(
        id=row.id,
        material_id=row.material_id,
        component_code=row.component_code,
        name=row.name or "",
        density_kg_l=row.density_kg_l,
        price_per_kg=row.price_per_kg,
        price_per_liter=row.price_per_liter,
        packaging_kg=row.packaging_kg,
        packaging_l=row.packaging_l,
        active=row.active,
    )


def _mix_to_domain(row: MaterialMixORM) -> MaterialMix:
    return MaterialMix(
        material_id=row.material_id,
        mix_ratio_a=row.mix_ratio_a,
        mix_ratio_b=row.mix_ratio_b,
        ratio_basis=row.ratio_basis,
        working_time_minutes=row.working_time_minutes,
        induction_time_minutes=row.induction_time_minutes,
        temperature_reference=row.temperature_reference,
        notes=row.notes or "",
    )


class TwoComponentRepository:
    """Читает только информационные данные о 2К-системах."""

    def __init__(self, session: Session):
        self.session = session

    def get_mix(self, material_id: int) -> Optional[MaterialMix]:
        row = self.session.scalar(
            select(MaterialMixORM).where(MaterialMixORM.material_id == material_id)
        )
        return _mix_to_domain(row) if row else None

    def get_components(self, material_id: int) -> list[MaterialComponent]:
        rows = self.session.scalars(
            select(MaterialComponentORM)
            .where(
                MaterialComponentORM.material_id == material_id,
                MaterialComponentORM.active.is_(True),
            )
            .order_by(MaterialComponentORM.component_code)
        ).all()
        return [_component_to_domain(row) for row in rows]

    def get_component(self, material_id: int, code: str) -> Optional[MaterialComponent]:
        row = self.session.scalar(
            select(MaterialComponentORM).where(
                MaterialComponentORM.material_id == material_id,
                MaterialComponentORM.component_code == code,
                MaterialComponentORM.active.is_(True),
            )
        )
        return _component_to_domain(row) if row else None
