"""Regression guards for unknown material thinner semantics."""
from __future__ import annotations

from app.domain.models import Material
from app.infrastructure.database.models import MaterialORM
from app.infrastructure.database.repositories import material_domain_to_orm, material_orm_to_domain


def test_material_domain_defaults_keep_thinner_fields_unknown():
    material = Material(material_name="Без данных")

    assert material.thinner_required is None
    assert material.thinner_name is None


def test_material_orm_thinner_fields_have_no_hidden_defaults():
    required_column = MaterialORM.__table__.c.thinner_required
    name_column = MaterialORM.__table__.c.thinner_name

    assert required_column.nullable is True
    assert required_column.default is None
    assert required_column.server_default is None
    assert name_column.nullable is True
    assert name_column.default is None
    assert name_column.server_default is None


def test_material_thinner_fields_round_trip_preserve_unknown_and_explicit_values():
    unknown = Material(material_name="Unknown", thinner_required=None, thinner_name=None)
    orm_unknown = material_domain_to_orm(unknown)
    assert orm_unknown.thinner_required is None
    assert orm_unknown.thinner_name is None
    round_trip_unknown = material_orm_to_domain(orm_unknown)
    assert round_trip_unknown.thinner_required is None
    assert round_trip_unknown.thinner_name is None

    explicit = Material(
        material_name="Explicit",
        thinner_required=True,
        thinner_name="Растворитель X",
    )
    orm_explicit = material_domain_to_orm(explicit)
    assert orm_explicit.thinner_required is True
    assert orm_explicit.thinner_name == "Растворитель X"
    round_trip_explicit = material_orm_to_domain(orm_explicit)
    assert round_trip_explicit.thinner_required is True
    assert round_trip_explicit.thinner_name == "Растворитель X"
