"""Repository layer for database access."""

from __future__ import annotations

from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from app.infrastructure.database.models import (
    MaterialORM, CoatingSystemORM, CoatingSystemLayerORM, CalculationORM,
    CalculationLayerORM, ComparisonORM, LayerCompatibilityORM, DictionaryORM,
    MaterialComponentORM, MaterialMixORM,
)
from app.domain.models import Material, CoatingSystem, LayerDefinition, MaterialComponent, MaterialMix
from app.domain.enums import MaterialType, BinderType, ApplicationMethod


def material_orm_to_domain(orm: MaterialORM) -> Material:
    return Material(
        id=orm.id, manufacturer=orm.manufacturer or "", brand=orm.brand or "",
        material_name=orm.material_name,
        material_type=MaterialType(orm.material_type) if orm.material_type else MaterialType.OTHER,
        binder_type=BinderType(orm.binder_type) if orm.binder_type else BinderType.UNKNOWN,
        description=orm.description or "", density=orm.density,
        solids_percent=orm.solids_percent,
        solids_by_volume_percent=orm.solids_by_volume_percent,
        voc=orm.voc, color=orm.color or "", ral=orm.ral or "",
        price_per_kg=orm.price_per_kg, price_per_liter=orm.price_per_liter,
        prices_include_vat=orm.prices_include_vat, theoretical_coverage=orm.theoretical_coverage,
        application_method=ApplicationMethod(orm.application_method) if orm.application_method else None,
        min_application_temperature=orm.min_application_temperature,
        max_application_temperature=orm.max_application_temperature,
        min_recoat_time_h=orm.min_recoat_time_h,
        max_recoat_time_h=orm.max_recoat_time_h,
        drying_time_h=orm.drying_time_h,
        full_cure_time_h=orm.full_cure_time_h,
        pot_life_h=orm.pot_life_h,
        induction_time_min=orm.induction_time_min,
        max_relative_humidity=orm.max_relative_humidity,
        min_dew_point_margin_c=orm.min_dew_point_margin_c,
        recommended_dft_min=orm.recommended_dft_min,
        recommended_dft_max=orm.recommended_dft_max,
        max_single_layer_dft=orm.max_single_layer_dft,
        thinner_required=orm.thinner_required,
        thinner_name=orm.thinner_name or "",
        thinner_percent_min=orm.thinner_percent_min,
        thinner_percent_max=orm.thinner_percent_max,
        thinner_basis=orm.thinner_basis or "BY_PAINT_VOLUME",
        packaging_kg=orm.packaging_kg, packaging_l=orm.packaging_l,
        is_two_component=orm.is_two_component,
        is_active=orm.is_active, is_incomplete=orm.is_incomplete,
        notes=orm.notes or "", datasheet=orm.datasheet or "",
        datasheet_version=orm.datasheet_version or "", datasheet_date=orm.datasheet_date,
        safety_data_sheet=orm.safety_data_sheet or "",
        certificate=orm.certificate or "", certificate_version=orm.certificate_version or "",
        test_protocol=orm.test_protocol or "",
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
    orm.solids_by_volume_percent = domain.solids_by_volume_percent
    orm.voc = domain.voc
    orm.color = domain.color
    orm.ral = domain.ral
    orm.price_per_kg = domain.price_per_kg
    orm.price_per_liter = domain.price_per_liter
    orm.prices_include_vat = domain.prices_include_vat
    orm.theoretical_coverage = domain.theoretical_coverage
    orm.application_method = domain.application_method.value if isinstance(domain.application_method, ApplicationMethod) else domain.application_method
    orm.min_application_temperature = domain.min_application_temperature
    orm.max_application_temperature = domain.max_application_temperature
    orm.min_recoat_time_h = domain.min_recoat_time_h
    orm.max_recoat_time_h = domain.max_recoat_time_h
    orm.drying_time_h = domain.drying_time_h
    orm.full_cure_time_h = domain.full_cure_time_h
    orm.pot_life_h = domain.pot_life_h
    orm.induction_time_min = domain.induction_time_min
    orm.max_relative_humidity = domain.max_relative_humidity
    orm.min_dew_point_margin_c = domain.min_dew_point_margin_c
    orm.recommended_dft_min = domain.recommended_dft_min
    orm.recommended_dft_max = domain.recommended_dft_max
    orm.max_single_layer_dft = domain.max_single_layer_dft
    orm.thinner_required = domain.thinner_required
    orm.thinner_name = domain.thinner_name
    orm.thinner_percent_min = domain.thinner_percent_min
    orm.thinner_percent_max = domain.thinner_percent_max
    orm.thinner_basis = domain.thinner_basis
    orm.packaging_kg = domain.packaging_kg
    orm.packaging_l = domain.packaging_l
    orm.is_two_component = domain.is_two_component
    orm.is_active = domain.is_active
    orm.is_incomplete = domain.is_incomplete
    orm.notes = domain.notes
    orm.datasheet = domain.datasheet
    orm.datasheet_version = domain.datasheet_version
    orm.datasheet_date = domain.datasheet_date
    orm.safety_data_sheet = domain.safety_data_sheet
    orm.certificate = domain.certificate
    orm.certificate_version = domain.certificate_version
    orm.test_protocol = domain.test_protocol
    orm.updated_at = datetime.utcnow()
    return orm


def material_component_orm_to_domain(orm: MaterialComponentORM) -> MaterialComponent:
    return MaterialComponent(
        id=orm.id, material_id=orm.material_id, component_code=orm.component_code,
        name=orm.name or "", density_kg_l=orm.density_kg_l,
        price_per_kg=orm.price_per_kg, price_per_liter=orm.price_per_liter,
        packaging_kg=orm.packaging_kg, packaging_l=orm.packaging_l, active=orm.active,
    )


def material_mix_orm_to_domain(orm: MaterialMixORM) -> MaterialMix:
    return MaterialMix(
        material_id=orm.material_id, mix_ratio_a=orm.mix_ratio_a, mix_ratio_b=orm.mix_ratio_b,
        ratio_basis=orm.ratio_basis or "mass", working_time_minutes=orm.working_time_minutes,
        induction_time_minutes=orm.induction_time_minutes,
        temperature_reference=orm.temperature_reference, notes=orm.notes or "",
    )


class MaterialRepository:
    def __init__(self, session:Session): self.session=session
    def get_by_id(self,material_id:int)->Optional[Material]:
        orm=self.session.get(MaterialORM,material_id); return material_orm_to_domain(orm) if orm else None
    def get_by_name(self,name:str)->Optional[Material]:
        orm=self.session.scalar(select(MaterialORM).where(MaterialORM.material_name==name)); return material_orm_to_domain(orm) if orm else None
    def list_all(self,active_only:bool=True)->list[Material]:
        stmt=select(MaterialORM).order_by(MaterialORM.material_name)
        if active_only:stmt=stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]
    def list_materials(self,active_only:bool=True)->list[Material]:
        stmt=select(MaterialORM).where(MaterialORM.material_type!=MaterialType.THINNER.value).order_by(MaterialORM.material_name)
        if active_only:stmt=stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]
    def list_thinners(self,active_only:bool=True)->list[Material]:
        stmt=select(MaterialORM).where(MaterialORM.material_type==MaterialType.THINNER.value).order_by(MaterialORM.material_name)
        if active_only:stmt=stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]
    def search(self,query:str,active_only:bool=True)->list[Material]:
        q=f"%{query.strip()}%";stmt=select(MaterialORM).where(or_(MaterialORM.material_name.ilike(q),MaterialORM.manufacturer.ilike(q),MaterialORM.brand.ilike(q),MaterialORM.binder_type.ilike(q),MaterialORM.ral.ilike(q))).order_by(MaterialORM.material_name)
        if active_only:stmt=stmt.where(MaterialORM.is_active.is_(True))
        return [material_orm_to_domain(o) for o in self.session.scalars(stmt)]
    def add(self,material:Material)->Material:
        orm=material_domain_to_orm(material);self.session.add(orm);self.session.flush();material.id=orm.id;return material
    def update(self,material:Material)->Material:
        if material.id is None:raise ValueError("Material.id is required for update")
        orm=self.session.get(MaterialORM,material.id)
        if orm is None:raise ValueError(f"Material id={material.id} not found")
        material_domain_to_orm(material,orm);self.session.flush();return material
    def delete(self,material_id:int,soft:bool=True)->None:
        orm=self.session.get(MaterialORM,material_id)
        if orm is None:return
        if soft:orm.is_active=False;orm.updated_at=datetime.utcnow()
        else:self.session.delete(orm)
        self.session.flush()
    def count(self,active_only:bool=True)->int:
        stmt=select(func.count(MaterialORM.id))
        if active_only:stmt=stmt.where(MaterialORM.is_active.is_(True))
        return self.session.scalar(stmt) or 0


class MaterialComponentRepository:
    """Информационные компоненты 2К; не выполняет закупочные расчёты."""
    def __init__(self, session: Session): self.session = session
    def list_for_material(self, material_id: int, active_only: bool = True) -> list[MaterialComponent]:
        stmt = select(MaterialComponentORM).where(MaterialComponentORM.material_id == material_id).order_by(MaterialComponentORM.component_code)
        if active_only: stmt = stmt.where(MaterialComponentORM.active.is_(True))
        return [material_component_orm_to_domain(o) for o in self.session.scalars(stmt)]
    def get(self, material_id: int, component_code: str) -> Optional[MaterialComponent]:
        orm = self.session.scalar(select(MaterialComponentORM).where(
            MaterialComponentORM.material_id == material_id,
            MaterialComponentORM.component_code == component_code,
        ))
        return material_component_orm_to_domain(orm) if orm else None


class MaterialMixRepository:
    """Справочные параметры смешения 2К без расчёта комплектов A/B."""
    def __init__(self, session: Session): self.session = session
    def get_for_material(self, material_id: int) -> Optional[MaterialMix]:
        orm = self.session.scalar(select(MaterialMixORM).where(MaterialMixORM.material_id == material_id))
        return material_mix_orm_to_domain(orm) if orm else None


class CoatingSystemRepository:
    def __init__(self,session:Session):self.session=session
    def get_by_id(self,system_id:int)->Optional[CoatingSystemORM]:return self.session.get(CoatingSystemORM,system_id)
    def list_all(self,active_only:bool=True)->Sequence[CoatingSystemORM]:
        stmt=select(CoatingSystemORM).order_by(CoatingSystemORM.system_name)
        if active_only:stmt=stmt.where(CoatingSystemORM.is_active.is_(True))
        return self.session.scalars(stmt).all()
    def search(self,query:str,active_only:bool=True)->Sequence[CoatingSystemORM]:
        q=f"%{query.strip()}%";stmt=select(CoatingSystemORM).where(or_(CoatingSystemORM.system_name.ilike(q),CoatingSystemORM.manufacturer.ilike(q),CoatingSystemORM.description.ilike(q))).order_by(CoatingSystemORM.system_name)
        if active_only:stmt=stmt.where(CoatingSystemORM.is_active.is_(True))
        return self.session.scalars(stmt).all()
    def add(self,system:CoatingSystemORM)->CoatingSystemORM:self.session.add(system);self.session.flush();return system
    def delete(self,system_id:int,soft:bool=True)->None:
        orm=self.session.get(CoatingSystemORM,system_id)
        if orm is None:return
        if soft:orm.is_active=False
        else:self.session.delete(orm)
        self.session.flush()


class CalculationRepository:
    def __init__(self,session:Session):self.session=session
    def list_recent(self,limit:int=50)->Sequence[CalculationORM]:return self.session.scalars(select(CalculationORM).order_by(CalculationORM.created_at.desc()).limit(limit)).all()
    def get_by_id(self,calc_id:int)->Optional[CalculationORM]:return self.session.get(CalculationORM,calc_id)
    def add(self,calc:CalculationORM)->CalculationORM:self.session.add(calc);self.session.flush();return calc
    def delete(self,calc_id:int)->None:
        orm=self.session.get(CalculationORM,calc_id)
        if orm:self.session.delete(orm);self.session.flush()


class CompatibilityRepository:
    def __init__(self,session:Session):self.session=session
    def get_status(self,from_binder:str,to_binder:str)->str:
        orm=self.session.scalar(select(LayerCompatibilityORM).where(LayerCompatibilityORM.from_binder==from_binder,LayerCompatibilityORM.to_binder==to_binder));return orm.status if orm else "нет подтвержденных данных"
    def list_all(self)->Sequence[LayerCompatibilityORM]:return self.session.scalars(select(LayerCompatibilityORM)).all()
    def set_status(self,from_binder:str,to_binder:str,status:str,notes:str="")->None:
        orm=self.session.scalar(select(LayerCompatibilityORM).where(LayerCompatibilityORM.from_binder==from_binder,LayerCompatibilityORM.to_binder==to_binder))
        if orm is None:self.session.add(LayerCompatibilityORM(from_binder=from_binder,to_binder=to_binder,status=status,notes=notes))
        else:orm.status=status;orm.notes=notes
        self.session.flush()
