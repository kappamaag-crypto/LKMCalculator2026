"""§19 legacy parity: material persistence v2 ↔ v3.

Shared: MaterialRepository CRUD over SQLite, get_by_name, soft delete.
Intentional v3: density / solids / price None stay None (UNKNOWN ≠ 0);
solids_by_volume_percent persisted; is_incomplete flag for controlled incomplete materials.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material
from app.infrastructure.database.engine import Base
from app.infrastructure.database.repositories import (
    MaterialRepository,
    material_domain_to_orm,
    material_orm_to_domain,
)
from app.infrastructure.database import models  # noqa: F401


def test_v2_and_v3_share_material_repository_api():
    root = Path(__file__).resolve().parents[2]
    v2 = (root / "v2" / "app" / "infrastructure" / "database" / "repositories.py").read_text(
        encoding="utf-8"
    )
    v3 = (root / "upload" / "app" / "infrastructure" / "database" / "repositories.py").read_text(
        encoding="utf-8"
    )
    assert "class MaterialRepository" in v2 and "class MaterialRepository" in v3
    for name in ("get_by_id", "get_by_name", "list_all", "add", "update", "delete"):
        assert f"def {name}" in v2 and f"def {name}" in v3
    assert "material_orm_to_domain" in v3 and "material_domain_to_orm" in v3


def test_v3_unknown_density_and_price_roundtrip_as_none():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    material = Material(
        material_name="Parity UNKNOWN props",
        manufacturer="Parity",
        material_type=MaterialType.PRIMER,
        binder_type=BinderType.EPOXY,
        density=None,
        solids_percent=None,
        solids_by_volume_percent=None,
        price_per_kg=None,
        price_per_liter=None,
    )
    with Session() as session:
        saved = MaterialRepository(session).add(material)
        session.commit()
        found = MaterialRepository(session).get_by_id(saved.id)
        assert found is not None
        assert found.density is None
        assert found.solids_percent is None
        assert found.solids_by_volume_percent is None
        assert found.price_per_kg is None
        assert found.price_per_liter is None


def test_v3_solids_by_volume_persisted():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    material = Material(
        material_name="Parity SV",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.3,
        solids_percent=70.0,
        solids_by_volume_percent=62.5,
        price_per_kg=400.0,
    )
    with Session() as session:
        saved = MaterialRepository(session).add(material)
        session.commit()
        found = MaterialRepository(session).get_by_name("Parity SV")
        assert found is not None
        assert found.solids_by_volume_percent == pytest.approx(62.5)
        assert found.density == pytest.approx(1.3)


def test_v3_soft_delete_hides_from_active_list():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        repo = MaterialRepository(session)
        m = repo.add(
            Material(
                material_name="To soft-delete",
                material_type=MaterialType.FINISH,
                binder_type=BinderType.POLYURETHANE,
                density=1.1,
                solids_by_volume_percent=55.0,
            )
        )
        session.commit()
        mid = m.id
        repo.delete(mid, soft=True)
        session.commit()
        active_ids = [x.id for x in repo.list_all(active_only=True)]
        assert mid not in active_ids


def test_v3_orm_mapping_does_not_coerce_none_to_zero():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        domain = Material(
            material_name="Map None",
            material_type=MaterialType.OTHER,
            binder_type=BinderType.UNKNOWN,
            density=None,
            price_per_kg=None,
        )
        orm = material_domain_to_orm(domain)
        session.add(orm)
        session.commit()
        session.refresh(orm)
        back = material_orm_to_domain(orm)
        assert back.density is None
        assert back.price_per_kg is None
