"""ORM models for reviewed engineering System Templates.

These tables are deliberately separate from the existing coating-system catalogue:
a confirmed template keeps provenance and review state and is not treated as a TDS.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.engine import Base


class SystemTemplateORM(Base):
    __tablename__ = "system_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    substrate: Mapped[str] = mapped_column(String(200), default="")
    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(300), nullable=False)
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CONFIRMED")
    notes: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    layers: Mapped[list["SystemTemplateLayerORM"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="SystemTemplateLayerORM.layer_number",
    )
    __table_args__ = (
        UniqueConstraint(
            "source_path", "source_sheet", "source_row", "source_sha256",
            name="uq_system_template_source",
        ),
    )


class SystemTemplateLayerORM(Base):
    __tablename__ = "system_template_layers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("system_templates.id", ondelete="CASCADE"), nullable=False
    )
    layer_number: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False
    )
    material_name: Mapped[str] = mapped_column(String(300), nullable=False)
    dft_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dft_target: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dft_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(300), nullable=False)
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    template: Mapped["SystemTemplateORM"] = relationship(back_populates="layers")
    __table_args__ = (
        UniqueConstraint("template_id", "layer_number", name="uq_system_template_layer_number"),
    )
