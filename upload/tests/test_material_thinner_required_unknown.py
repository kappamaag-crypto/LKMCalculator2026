"""Regression guards for unknown material thinner requirement semantics."""
from __future__ import annotations

from app.domain.models import Material
from app.infrastructure.database.models import MaterialORM
from app.infrastructure.database.repositories import material_domain_to_orm, material_orm_to_domain


def test_material_domain_default_keeps_thinner_requirement_unknown():
    material = Material(material_name="Без данных")

    assert material.thinner_required is None


def test_material_orm_thinner_requirement_has_no_hidden_default():
    column = MaterialORM.__table__.c.thinner_required

    assert column.nullable is True
    assert column.default is None
    assert column.server_default is None


def test_material_thinner_requirement_round_trip_preserves_unknown_and_explicit_values():
    unknown = Material(material_name="Unknown", thinner_required=None)
    orm_unknown = material_domain_to_orm(unknown)
    assert orm_unknown.thinner_required is None
    assert material_orm_to_domain(orm_unknown).thinner_required is None

    for required in (False, True):
        material = Material(material_name=f"Explicit {required}", thinner_required=required)
        orm = material_domain_to_orm(material)
        assert orm.thinner_required is required
        assert material_orm_to_domain(orm).thinner_required is required
