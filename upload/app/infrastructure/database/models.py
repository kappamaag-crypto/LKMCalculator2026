"""SQLAlchemy ORM models for the v3 domain."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Table, Column, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database.engine import Base

material_corrosion = Table("material_corrosion", Base.metadata, Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True), Column("category", String(20), primary_key=True))
material_durability = Table("material_durability", Base.metadata, Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True), Column("level", String(20), primary_key=True))
material_surface = Table("material_surface", Base.metadata, Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True), Column("surface_type", String(50), primary_key=True))
material_environment = Table("material_environment", Base.metadata, Column("material_id", ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True), Column("environment", String(50), primary_key=True))
system_corrosion = Table("system_corrosion", Base.metadata, Column("system_id", ForeignKey("coating_systems.id", ondelete="CASCADE"), primary_key=True), Column("category", String(20), primary_key=True))
system_environment = Table("system_environment", Base.metadata, Column("system_id", ForeignKey("coating_systems.id", ondelete="CASCADE"), primary_key=True), Column("environment", String(50), primary_key=True))
system_surface = Table("system_surface", Base.metadata, Column("system_id", ForeignKey("coating_systems.id", ondelete="CASCADE"), primary_key=True), Column("surface_type", String(50), primary_key=True))

class MaterialORM(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    manufacturer: Mapped[str] = mapped_column(String(200), default="")
    brand: Mapped[str] = mapped_column(String(200), default="")
    material_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    material_type: Mapped[str] = mapped_column(String(50), default="прочее")
    binder_type: Mapped[str] = mapped_column(String(50), default="не указано")
    description: Mapped[str] = mapped_column(Text, default="")
    density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solids_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    solids_by_volume_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    voc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    color: Mapped[str] = mapped_column(String(100), default="")
    ral: Mapped[str] = mapped_column(String(50), default="")
    price_per_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_per_liter: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prices_include_vat: Mapped[bool] = mapped_column(Boolean, default=True)
    theoretical_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    application_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    min_application_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_application_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_recoat_time_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_recoat_time_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drying_time_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    full_cure_time_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pot_life_h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    induction_time_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_relative_humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_dew_point_margin_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_dft_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_dft_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_single_layer_dft: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thinner_required: Mapped[bool] = mapped_column(Boolean, default=False)
    thinner_name: Mapped[str] = mapped_column(String(200), default="")
    thinner_percent_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thinner_percent_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thinner_basis: Mapped[str] = mapped_column(String(40), default="BY_PAINT_VOLUME")
    packaging_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    packaging_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_two_component: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_incomplete: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    datasheet: Mapped[str] = mapped_column(String(500), default="")
    datasheet_version: Mapped[str] = mapped_column(String(100), default="")
    datasheet_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    safety_data_sheet: Mapped[str] = mapped_column(String(500), default="")
    certificate: Mapped[str] = mapped_column(String(500), default="")
    certificate_version: Mapped[str] = mapped_column(String(100), default="")
    test_protocol: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoatingSystemORM(Base):
    __tablename__ = "coating_systems"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    durability: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    substrate: Mapped[str] = mapped_column(String(200), default="")
    total_dft_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_dft_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_dft_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    number_of_layers: Mapped[int] = mapped_column(Integer, default=0)
    temperature_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    standards: Mapped[str] = mapped_column(String(300), default="")
    certificate: Mapped[str] = mapped_column(String(300), default="")
    technical_document: Mapped[str] = mapped_column(String(300), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    layers: Mapped[list["CoatingSystemLayerORM"]] = relationship(back_populates="system", cascade="all, delete-orphan", order_by="CoatingSystemLayerORM.layer_number")

class CoatingSystemLayerORM(Base):
    __tablename__ = "coating_system_layers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("coating_systems.id", ondelete="CASCADE"))
    layer_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[Optional[int]] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    layer_type: Mapped[str] = mapped_column(String(50), default="прочее")
    dft_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dft_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_dft: Mapped[float] = mapped_column(Float, default=0.0)
    thinner_percent: Mapped[float] = mapped_column(Float, default=0.0)
    thinner_material_id: Mapped[Optional[int]] = mapped_column(ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    thinner_basis: Mapped[str] = mapped_column(String(40), default="BY_PAINT_VOLUME")
    passes: Mapped[int] = mapped_column(Integer, default=1)
    application_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    system: Mapped["CoatingSystemORM"] = relationship(back_populates="layers")
    __table_args__ = (UniqueConstraint("system_id", "layer_number", name="uq_system_layer_number"),)

class LayerCompatibilityORM(Base):
    __tablename__ = "layer_compatibility"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_binder: Mapped[str] = mapped_column(String(50), nullable=False)
    to_binder: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="нет подтвержденных данных")
    notes: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("from_binder", "to_binder", name="uq_binder_pair"),)

class CalculationORM(Base):
    __tablename__ = "calculations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calculation_number: Mapped[str] = mapped_column(String(100), default="")
    object_name: Mapped[str] = mapped_column(String(300), default="")
    customer: Mapped[str] = mapped_column(String(300), default="")
    project: Mapped[str] = mapped_column(String(300), default="")
    area_m2: Mapped[float] = mapped_column(Float, default=0.0)
    system_id: Mapped[Optional[int]] = mapped_column(ForeignKey("coating_systems.id", ondelete="SET NULL"), nullable=True)
    system_name: Mapped[str] = mapped_column(String(300), default="")
    total_dft: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost_per_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_consumption_kg: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    layers: Mapped[list["CalculationLayerORM"]] = relationship(back_populates="calculation", cascade="all, delete-orphan", order_by="CalculationLayerORM.layer_number")

class CalculationLayerORM(Base):
    __tablename__ = "calculation_layers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calculation_id: Mapped[int] = mapped_column(ForeignKey("calculations.id", ondelete="CASCADE"))
    layer_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_name: Mapped[str] = mapped_column(String(300), default="")
    binder: Mapped[str] = mapped_column(String(50), default="")
    dry_thickness: Mapped[float] = mapped_column(Float, default=0.0)
    consumption_kg: Mapped[float] = mapped_column(Float, default=0.0)
    consumption_l: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_m2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    calculation: Mapped["CalculationORM"] = relationship(back_populates="layers")

class ComparisonORM(Base):
    __tablename__ = "comparisons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_name: Mapped[str] = mapped_column(String(300), default="")
    area_m2: Mapped[float] = mapped_column(Float, default=0.0)
    systems_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DictionaryORM(Base):
    __tablename__ = "dictionaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), default="")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("dict_type", "name", name="uq_dict_type_name"),)

class MaterialComponentORM(Base):
    __tablename__ = "material_components"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True)
    component_code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    density_kg_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_per_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_per_liter: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    packaging_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    packaging_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("material_id", "component_code", name="uq_material_component_code"),)

class MaterialMixORM(Base):
    __tablename__ = "material_mixes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, unique=True)
    mix_ratio_a: Mapped[float] = mapped_column(Float, nullable=False)
    mix_ratio_b: Mapped[float] = mapped_column(Float, nullable=False)
    ratio_basis: Mapped[str] = mapped_column(String(20), default="mass")
    working_time_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    induction_time_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature_reference: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

class PackageORM(Base):
    __tablename__ = "packages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[Optional[int]] = mapped_column(ForeignKey("materials.id", ondelete="CASCADE"), nullable=True)
    component_id: Mapped[Optional[int]] = mapped_column(ForeignKey("material_components.id", ondelete="CASCADE"), nullable=True)
    package_name: Mapped[str] = mapped_column(String(200), default="")
    net_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_volume_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    units_per_set: Mapped[int] = mapped_column(Integer, default=1)
    package_type: Mapped[str] = mapped_column(String(30), default="single")
    is_component_package: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class CalculationSnapshotORM(Base):
    __tablename__ = "calculation_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    calculation_id: Mapped[int] = mapped_column(ForeignKey("calculations.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project_name: Mapped[str] = mapped_column(String(300), default="")
    object_data_json: Mapped[str] = mapped_column(Text, default="{}")
    system_data_json: Mapped[str] = mapped_column(Text, default="{}")
    materials_data_json: Mapped[str] = mapped_column(Text, default="{}")
    formula_version: Mapped[str] = mapped_column(String(30), default="3.0")
    calculator_version: Mapped[str] = mapped_column(String(30), default="3.0.0")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
