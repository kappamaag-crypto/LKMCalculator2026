"""Инженерные регрессионные тесты валидации v3."""

import pytest

from app.domain.enums import BinderType, MaterialType
from app.domain.models import CoatingSystem, LayerDefinition, Material, ObjectData
from app.domain.validation import (
    validate_application_conditions,
    validate_layer_input,
    validate_material,
    validate_system_layers,
)


def make_material(**kwargs):
    data = dict(
        material_name="Test coating",
        material_type=MaterialType.PRIMER,
        binder_type=BinderType.EPOXY,
        density=1.4,
        solids_percent=70.0,
        thinner_basis="BY_PAINT_VOLUME",
    )
    data.update(kwargs)
    return Material(**data)


def test_solids_by_volume_must_be_0_to_100():
    result = validate_material(make_material(solids_by_volume_percent=101))
    assert any(i.code == "MAT_SV_GT100" and i.level == "error" for i in result.issues)


def test_thinner_above_material_max_is_error():
    material = make_material(thinner_percent_max=15.0)
    result = validate_layer_input(material, 100.0, thinner_percent=20.0)
    assert any(i.code == "LAYER_THINNER_ABOVE_MAX" and i.level == "error" for i in result.issues)


def test_mix_volume_basis_requires_less_than_100_percent():
    material = make_material(thinner_basis="BY_MIX_VOLUME")
    result = validate_layer_input(material, 100.0, thinner_percent=100.0)
    assert any(i.code == "LAYER_MIX_DILUTION_INVALID" for i in result.issues)


def test_application_conditions_check_temperature_rh_and_dew_point_margin():
    material = make_material(
        min_application_temperature=10.0,
        max_relative_humidity=80.0,
        min_dew_point_margin_c=3.0,
    )
    obj = ObjectData(
        surface_temperature=8.0,
        dew_point=6.0,
        relative_humidity=85.0,
    )
    result = validate_application_conditions(obj, material)
    codes = {i.code for i in result.issues}
    assert "COND_TEMP_BELOW_MIN" in codes
    assert "COND_RH_ABOVE_MAX" in codes
    assert "COND_DEW_MARGIN" in codes


def test_system_total_dft_is_checked():
    material = make_material(recommended_dft_min=80.0, recommended_dft_max=160.0)
    system = CoatingSystem(
        system_name="System A",
        number_of_layers=1,
        total_dft_min=120.0,
        total_dft_max=300.0,
    )
    layer = LayerDefinition(material=material, target_dft=100.0)
    result = validate_system_layers([layer], system=system)
    assert any(i.code == "SYS_TOTAL_DFT_BELOW_MIN" for i in result.issues)


def test_system_layer_count_is_checked():
    material = make_material()
    system = CoatingSystem(system_name="System A", number_of_layers=2)
    layer = LayerDefinition(material=material, target_dft=100.0)
    result = validate_system_layers([layer], system=system)
    assert any(i.code == "SYS_LAYER_COUNT" for i in result.issues)
