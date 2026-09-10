import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.models import Material, MaterialComponent, MaterialMix, ObjectData
from app.domain.enums import BinderType, MaterialType
from app.domain.calculator import LayerInput
from app.domain.two_component import (
    RATIO_MASS,
    RATIO_VOLUME,
    TwoComponentCalculationError,
    TwoComponentService,
)
from app.services.calculation_service import CalculationService
from app.infrastructure.database.engine import Base
from app.infrastructure.database.models import MaterialORM, MaterialComponentORM, MaterialMixORM
from app.infrastructure.database.repositories import (
    MaterialComponentRepository,
    MaterialMixRepository,
    material_orm_to_domain,
)


def _materials():
    two_k = Material(
        manufacturer="Blank",
        material_name="2К Эпоксидный материал",
        material_type=MaterialType.PRIMER_ENAMEL,
        binder_type=BinderType.EPOXY,
        density=1.45,
        solids_by_volume_percent=72.0,
        price_per_kg=500.0,
        is_two_component=True,
    )
    finish = Material(
        manufacturer="Blank",
        material_name="Финиш",
        material_type=MaterialType.FINISH,
        binder_type=BinderType.POLYURETHANE,
        density=1.3,
        solids_by_volume_percent=60.0,
        price_per_kg=700.0,
    )
    return two_k, finish


def test_two_component_is_information_only():
    result = TwoComponentService.describe(
        mix=MaterialMix(material_id=1, mix_ratio_a=4.0, mix_ratio_b=1.0, ratio_basis=RATIO_MASS, working_time_minutes=40),
        component_a=MaterialComponent(component_code="A", name="Base"),
        component_b=MaterialComponent(component_code="B", name="Hardener"),
    )
    assert result.ratio_text == "4:1 по массе"
    assert result.component_a.name == "Base"
    assert result.component_b.name == "Hardener"
    assert result.working_time_minutes == 40
    assert not hasattr(result, "purchase_a_kg")
    assert not hasattr(result, "remainder_a_kg")
    assert not hasattr(result, "sets")


def test_two_component_volume_ratio_is_supported():
    result = TwoComponentService.describe(
        mix=MaterialMix(material_id=1, mix_ratio_a=2.0, mix_ratio_b=1.0, ratio_basis=RATIO_VOLUME, induction_time_minutes=20),
        component_a=MaterialComponent(component_code="A"),
        component_b=MaterialComponent(component_code="B"),
    )
    assert result.ratio_text == "2:1 по объёму"
    assert result.induction_time_minutes == 20


def test_two_component_invalid_ratio_is_rejected():
    with pytest.raises(TwoComponentCalculationError):
        TwoComponentService.describe(
            mix=MaterialMix(material_id=1, mix_ratio_a=0.0, mix_ratio_b=1.0),
            component_a=MaterialComponent(component_code="A"),
            component_b=MaterialComponent(component_code="B"),
        )


def test_two_component_invalid_basis_is_rejected():
    with pytest.raises(TwoComponentCalculationError):
        TwoComponentService.describe(
            mix=MaterialMix(material_id=1, mix_ratio_a=4.0, mix_ratio_b=1.0, ratio_basis="unknown"),
            component_a=MaterialComponent(component_code="A"),
            component_b=MaterialComponent(component_code="B"),
        )


def test_two_component_material_calculates_as_one_layer_in_multilayer_system():
    two_k, finish = _materials()
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name="2К тест", area_m2=100.0),
        [
            LayerInput(material=two_k, target_dft=120.0, losses_percent=5.0),
            LayerInput(material=finish, target_dft=80.0, losses_percent=5.0),
        ],
    )
    assert not validation.has_errors
    assert len(result.layers) == 2
    assert result.layers[0].material.is_two_component is True
    assert result.layers[0].practical_consumption_kg > 0
    assert result.layers[0].practical_consumption_l > 0
    assert result.total_practical_consumption_kg > result.layers[0].practical_consumption_kg


@pytest.mark.parametrize("layer_count,two_k_index", [(2, 0), (2, 1), (3, 0), (3, 1), (3, 2), (4, 0), (4, 2), (4, 3), (5, 0), (5, 2), (5, 4)])
def test_two_component_remains_one_layer_at_any_position_in_multilayer_system(layer_count, two_k_index):
    two_k, finish = _materials()
    layers = [
        LayerInput(material=(two_k if index == two_k_index else finish), target_dft=100.0 + index * 20.0, losses_percent=5.0)
        for index in range(layer_count)
    ]
    result, validation = CalculationService().calculate_system(
        ObjectData(object_name=f"2К {layer_count} слоёв", area_m2=100.0),
        layers,
    )
    assert not validation.has_errors
    assert len(result.layers) == layer_count
    assert sum(layer.material.is_two_component for layer in result.layers) == 1
    assert result.layers[two_k_index].material.is_two_component is True
    assert all(layer.practical_consumption_kg > 0 for layer in result.layers)
    assert all(layer.practical_consumption_l > 0 for layer in result.layers)


def test_two_component_database_metadata_round_trip_is_informational_only():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        material = MaterialORM(
            manufacturer="Blank", material_name="2К Эпоксидный материал",
            material_type=MaterialType.PRIMER_ENAMEL.value, binder_type=BinderType.EPOXY.value,
            density=1.45, solids_by_volume_percent=72.0, price_per_kg=500.0,
            is_two_component=True,
        )
        session.add(material)
        session.flush()
        session.add_all([
            MaterialComponentORM(material_id=material.id, component_code="A", name="Основа", density_kg_l=1.5),
            MaterialComponentORM(material_id=material.id, component_code="B", name="Отвердитель", density_kg_l=1.1),
            MaterialMixORM(material_id=material.id, mix_ratio_a=4.0, mix_ratio_b=1.0, ratio_basis=RATIO_MASS, working_time_minutes=40),
        ])
        session.commit()

        loaded = material_orm_to_domain(session.get(MaterialORM, material.id))
        components = MaterialComponentRepository(session).list_for_material(material.id)
        mix = MaterialMixRepository(session).get_for_material(material.id)

    assert loaded.is_two_component is True
    assert [component.component_code for component in components] == ["A", "B"]
    assert mix is not None
    assert (mix.mix_ratio_a, mix.mix_ratio_b, mix.ratio_basis) == (4.0, 1.0, RATIO_MASS)
    assert not hasattr(mix, "purchase_a_kg")
    assert not hasattr(mix, "sets")
