import pytest

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
