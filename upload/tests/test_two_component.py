import pytest

from app.domain.models import MaterialComponent, MaterialMix
from app.domain.two_component import (
    RATIO_MASS,
    RATIO_VOLUME,
    TwoComponentCalculationError,
    TwoComponentService,
)


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
