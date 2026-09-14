from app.infrastructure.database.models import MaterialORM


def test_material_thinner_basis_has_no_hidden_defaults():
    column = MaterialORM.__table__.c.thinner_basis

    assert column.nullable is True
    assert column.default is None
    assert column.server_default is None
