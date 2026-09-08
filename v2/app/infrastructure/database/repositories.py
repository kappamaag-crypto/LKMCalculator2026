"""Repository layer for database access."""

from __future__ import annotations

from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    MaterialORM, CoatingSystemORM, CoatingSystemLayerORM,
    CalculationORM, CalculationLayerORM, ComparisonORM,
    LayerCompatibilityORM, DictionaryORM,
)
from app.domain.models import Material, CoatingSystem, LayerDefinition
from app.domain.enums import MaterialType, BinderType


def material_orm_to_domain(orm: MaterialORM) -> Material:
    return Material(
        id=orm.id, manufacturer=orm.manufacturer or "", brand=orm.brand or "",
        material_name=orm.material_name,
        material_type=MaterialType(orm.material_type) if orm.material_type else MaterialType.OTHER,
        binder_type=BinderType(orm.binder_type) if orm.binder_type else BinderType.UNKNOWN,
        description=orm.description or "", density=orm.density or 0.0,
        solids_percent=orm.solids_percent or 0.0, voc=orm.voc,
        color=orm.color or "", ral=orm.ral or "",
        price_per_kg=orm.price_per_kg, price_per_liter=orm.price_per_liter,
        prices_include_vat=orm.prices_include_vat,
        theoretical_coverage=orm.theoretical_coverage,
        recommended_dft_min=orm.recommended_dft_min, recommended_dft_max=orm.recommended_dft_max,
        max_single_layer_dft=orm.max_single_layer_dft,
        thinner_required=orm.thinner_required, thinner_name=orm.thinner_name or "",
        thinner_percent_min=orm.thinner_percent_min, thinner_percent_max=orm.thinner_percent_max,
        packaging_kg=orm.packaging_kg, packaging_l=orm.packaging_l,
        is_active=orm.is_active, is_incomplete=orm.is_incomplete,
        notes=orm.notes or "", datasheet=orm.datasheet or "", certificate=orm.certificate or "",
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


def material_domain_to_orm(domain: Material, orm: Optional[MaterialORM] = None) -> MaterialORM:
    if orm is None:
        orm = MaterialORM()
    orm.manufacturer = domain.manufacturer
    orm.brand = domain.brand
    orm.material_name = domain.material_name
    orm.material_type = domain.material_type.value if isinstance(domain.material_type, MaterialType) else str(domain.material_type)
    orm.binder_type = domain.binder_type.value if isinstance(domain.binder_type, BinderType) else str(domain.binder_type)
    orm.description = domain.description
    orm.density = domain.density
    orm.solids_percent = domain.solids_percent
    orm.voc = domain.voc
    orm.color = domain.color
    orm.ral = domain.ral
    orm.price_per_kg = domain.price_per_kg
    orm.price_per_liter = domain.price_per_liter
    orm.prices_include_vat = domain.prices_include_vat
    orm.theoretical_coverage = domain.theoretical_coverage
    orm.recommended_dft_min = domain.recommended_dft_min
    orm.recommended_dft_max = domain.recommended_dft_max
    orm.max_single_layer_dft = domain.max_single_layer_dft
    orm.thinner_required = domain.thinner_required
    orm.thinner_name = domain.thinner_name
    orm.thinner_percent_min = domain.thinner_percent_min
    orm.thinner_percent_max = domain.thinner_percent_max
    orm.packaging_kg = domain.packaging_kg
    orm.packaging_l = domain.packaging_l
    orm.is_active = domain.is_active
    orm.is_incomplete = domain.is_incomplete
    orm.notes = domain.notes
    orm.datasheet = domain.datasheet
    orm.certificate = domain.certificate
    orm.updated_at = datetime.utcnow()
    return orm


class MaterialRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, material_id: int) -> Optional[Material]:
        orm = self.session.get(MaterialORM, material_id)
        return material_orm_to_domain(orm) if orm else None

    def get_by_name(self, name: str) -> Optional[Material]:
        orm = self.session.scalar(select(MaterialORM).where(MaterialORM.material_name == name))
        return material_orm_to_domain(orm) if orm else None

    def list_all(self, active_only: bool = True) -> list[Material]:
        stmt = select(MaterialORM).order_by(MaterialORM.material_name)
        if active_only:
            stmt = stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]

    def list_materials(self, active_only: bool = True) -> list[Material]:
        stmt = select(MaterialORM).where(MaterialORM.material_type != MaterialType.THINNER.value).order_by(MaterialORM.material_name)
        if active_only:
            stmt = stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]

    def list_thinners(self, active_only: bool = True) -> list[Material]:
        stmt = select(MaterialORM).where(MaterialORM.material_type == MaterialType.THINNER.value).order_by(MaterialORM.material_name)
        if active_only:
            stmt = stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]

    def search(self, query: str, active_only: bool = True) -> list[Material]:
        q = f"%{query.strip()}%"
        stmt = select(MaterialORM).where(or_(
            MaterialORM.material_name.ilike(q), MaterialORM.manufacturer.ilike(q),
            MaterialORM.brand.ilike(q), MaterialORM.binder_type.ilike(q), MaterialORM.ral.ilike(q),
        )).order_by(MaterialORM.material_name)
        if active_only:
            stmt = stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]

    def add(self, material: Material) -> Material:
        orm = material_domain_to_orm(material)
        self.session.add(orm)
        self.session.flush()
        material.id = orm.id
        return material

    def update(self, material: Material) -> Material:
        if material.id is None:
            raise ValueError("Material.id is required for update")
        orm = self.session.get(MaterialORM, material.id)
        if orm is None:
            raise ValueError(f"Material id={material.id} not found")
        material_domain_to_orm(material, orm)
        self.session.flush()
        return material

    def delete(self, material_id: int, soft: bool = True) -> None:
        orm = self.session.get(MaterialORM, material_id)
        if orm is None:
            return
        if soft:
            orm.is_active = False
            orm.updated_at = datetime.utcnow()
        else:
            self.session.delete(orm)
        self.session.flush()

    def count(self, active_only: bool = True) -> int:
        stmt = select(func.count(MaterialORM.id))
        if active_only:
            stmt = stmt.where(MaterialORM.is_active.is_(True))
        return self.session.scalar(stmt) or 0


class CoatingSystemRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, system_id: int) -> Optional[CoatingSystemORM]:
        return self.session.get(CoatingSystemORM, system_id)

    def list_all(self, active_only: bool = True) -> Sequence[CoatingSystemORM]:
        stmt = select(CoatingSystemORM).order_by(CoatingSystemORM.system_name)
        if active_only:
            stmt = stmt.where(CoatingSystemORM.is_active.is_(True))
        return self.session.scalars(stmt).all()

    def search(self, query: str, active_only: bool = True) -> Sequence[CoatingSystemORM]:
        q = f"%{query.strip()}%"
        stmt = select(CoatingSystemORM).where(or_(
            CoatingSystemORM.system_name.ilike(q), CoatingSystemORM.manufacturer.ilike(q),
            CoatingSystemORM.description.ilike(q),
        )).order_by(CoatingSystemORM.system_name)
        if active_only:
            stmt = stmt.where(CoatingSystemORM.is_active.is_(True))
        return self.session.scalars(stmt).all()

    def add(self, system: CoatingSystemORM) -> CoatingSystemORM:
        self.session.add(system)
        self.session.flush()
        return system

    def delete(self, system_id: int, soft: bool = True) -> None:
        orm = self.session.get(CoatingSystemORM, system_id)
        if orm is None:
            return
        if soft:
            orm.is_active = False
        else:
            self.session.delete(orm)
        self.session.flush()


class CalculationRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_recent(self, limit: int = 50) -> Sequence[CalculationORM]:
        stmt = select(CalculationORM).order_by(CalculationORM.created_at.desc()).limit(limit)
        return self.session.scalars(stmt).all()

    def get_by_id(self, calc_id: int) -> Optional[CalculationORM]:
        return self.session.get(CalculationORM, calc_id)

    def add(self, calc: CalculationORM) -> CalculationORM:
        self.session.add(calc)
        self.session.flush()
        return calc

    def delete(self, calc_id: int) -> None:
        orm = self.session.get(CalculationORM, calc_id)
        if orm:
            self.session.delete(orm)
            self.session.flush()


class CompatibilityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_status(self, from_binder: str, to_binder: str) -> str:
        stmt = select(LayerCompatibilityORM).where(
            LayerCompatibilityORM.from_binder == from_binder,
            LayerCompatibilityORM.to_binder == to_binder,
        )
        orm = self.session.scalar(stmt)
        if orm is None:
            return "\u043d\u0435\u0442 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u043d\u044b\u0445 \u0434\u0430\u043d\u043d\u044b\u0445"
        return orm.status

    def list_all(self) -> Sequence[LayerCompatibilityORM]:
        return self.session.scalars(select(LayerCompatibilityORM)).all()

    def set_status(self, from_binder: str, to_binder: str, status: str, notes: str = "") -> None:
        stmt = select(LayerCompatibilityORM).where(
            LayerCompatibilityORM.from_binder == from_binder,
            LayerCompatibilityORM.to_binder == to_binder,
        )
        orm = self.session.scalar(stmt)
        if orm is None:
            self.session.add(LayerCompatibilityORM(from_binder=from_binder, to_binder=to_binder, status=status, notes=notes))
        else:
            orm.status = status
            orm.notes = notes
        self.session.flush()
