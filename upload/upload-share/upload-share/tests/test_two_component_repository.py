from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.database.engine import Base
from app.infrastructure.database.models import MaterialORM, MaterialComponentORM, MaterialMixORM
from app.infrastructure.database.two_component_repository import TwoComponentRepository
from app.services.two_component_service import TwoComponentService


def test_two_component_repository_reads_mix_and_components():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        material = MaterialORM(
            manufacturer="Veksa",
            brand="Veksa",
            material_name="VEKSA PP 11",
            material_type="наливной пол",
            binder_type="эпоксид",
            is_two_component=True,
        )
        session.add(material)
        session.flush()
        session.add(MaterialMixORM(
            material_id=material.id,
            mix_ratio_a=4.7,
            mix_ratio_b=1.0,
            ratio_basis="mass",
            working_time_minutes=40,
            notes="Источник TDS",
        ))
        session.add_all([
            MaterialComponentORM(material_id=material.id, component_code="A", name="Компонент A"),
            MaterialComponentORM(material_id=material.id, component_code="B", name="Компонент B"),
        ])
        session.commit()

        repo = TwoComponentRepository(session)
        mix = repo.get_mix(material.id)
        components = repo.get_components(material.id)

        assert mix is not None
        assert mix.mix_ratio_a == 4.7
        assert mix.mix_ratio_b == 1.0
        assert mix.ratio_basis == "mass"
        assert mix.working_time_minutes == 40
        assert [c.component_code for c in components] == ["A", "B"]

        result = TwoComponentService.describe_from_database(session, material.id)
        assert result is not None
        assert result.ratio_text == "4.7:1 по массе"
        assert result.component_a.name == "Компонент A"
        assert result.component_b.name == "Компонент B"


def test_two_component_repository_returns_none_without_mix():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        material = MaterialORM(material_name="2K без метаданных", is_two_component=True)
        session.add(material)
        session.commit()
        assert TwoComponentService.describe_from_database(session, material.id) is None
