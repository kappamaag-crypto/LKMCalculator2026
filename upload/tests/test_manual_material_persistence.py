"""Проверка сохранения ЛКМ, введённых пользователем вручную."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.enums import BinderType, MaterialType
from app.domain.models import Material
from app.infrastructure.database.engine import Base
from app.infrastructure.database.repositories import MaterialRepository
from app.infrastructure.database import models  # noqa: F401


def test_manual_material_roundtrip_and_no_duplicate():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    material = Material(
        material_name="Пользовательский ЛКМ Test",
        manufacturer="Test manufacturer",
        material_type=MaterialType.PRIMER,
        binder_type=BinderType.EPOXY,
        density=1.42,
        solids_percent=72.0,
        solids_by_volume_percent=64.0,
        price_per_kg=650.0,
        recommended_dft_min=80.0,
        recommended_dft_max=160.0,
    )

    with Session() as session:
        repo = MaterialRepository(session)
        saved = repo.add(material)
        session.commit()
        saved_id = saved.id

        found = repo.get_by_name(material.material_name)
        assert found is not None
        assert found.id == saved_id
        assert found.solids_by_volume_percent == 64.0
        assert found.price_per_kg == 650.0

        duplicate = repo.get_by_name(material.material_name)
        assert duplicate is not None
        assert duplicate.id == saved_id
        assert repo.count(active_only=True) == 1
